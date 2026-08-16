"""Tests del saneador de esquemas para Odoo.

Cada aserción refleja una restricción REAL verificada contra el Odoo de
Efficax el 15-ago-2026 (no supuestos): si Odoo rechaza la construcción, el
saneador tiene que haberla eliminado o traducido.
"""
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from esquemas_odoo import (  # noqa: E402
    CLAVES_PERMITIDAS_PROPIEDAD,
    EsquemaNoTraducible,
    sanear_para_odoo,
)
from generador import catalogo_path  # noqa: E402

DEFS = {
    "periodo": {
        "type": "object",
        "properties": {
            "desde": {"type": "string", "format": "date"},
            "hasta": {"type": "string", "format": "date"},
        },
        "required": ["desde", "hasta"],
    },
    "moneda": {"type": "string", "enum": ["PEN", "USD"], "default": "PEN"},
}


def test_required_siempre_presente():
    """Odoo rechaza el esquema si falta `required`, aunque no haya obligatorios."""
    out = sanear_para_odoo({"type": "object", "properties": {}})
    assert out["required"] == []
    assert out["type"] == "object"


def test_elimina_claves_no_soportadas():
    entrada = {
        "properties": {
            "texto": {"type": "string", "minLength": 30, "format": "email"},
            "monto": {"type": "number", "exclusiveMinimum": 0, "default": 5},
        },
        "required": ["texto"],
    }
    out = sanear_para_odoo(entrada)
    for prop in out["properties"].values():
        assert set(prop.keys()) <= CLAVES_PERMITIDAS_PROPIEDAD


def test_restricciones_se_trasladan_a_la_descripcion():
    """No se pierden: si Odoo no las hace cumplir, al menos el modelo las lee."""
    out = sanear_para_odoo(
        {"properties": {"resumen": {"type": "string", "minLength": 30}}, "required": []}
    )
    assert "30" in out["properties"]["resumen"]["description"]


def test_ref_se_resuelve_y_objeto_anidado_se_aplana():
    entrada = {"properties": {"periodo": {"$ref": "#/$defs/periodo"}}, "required": ["periodo"]}
    out = sanear_para_odoo(entrada, DEFS)
    assert "periodo_desde" in out["properties"]
    assert "periodo_hasta" in out["properties"]
    assert "periodo" not in out["properties"]
    # el obligatorio original se propaga a los dos derivados
    assert set(out["required"]) == {"periodo_desde", "periodo_hasta"}


def test_ref_a_escalar_conserva_enum():
    out = sanear_para_odoo({"properties": {"moneda": {"$ref": "#/$defs/moneda"}}, "required": []}, DEFS)
    assert out["properties"]["moneda"]["enum"] == ["PEN", "USD"]
    assert "default" not in out["properties"]["moneda"]


def test_array_de_objetos_se_vuelve_un_string_json():
    entrada = {
        "properties": {
            "lineas": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {"sku": {"type": "string"}, "cantidad": {"type": "number"}},
                    "required": ["sku", "cantidad"],
                },
            }
        },
        "required": ["lineas"],
    }
    out = sanear_para_odoo(entrada)
    assert "lineas_json" in out["properties"]
    assert out["properties"]["lineas_json"]["type"] == "string"
    assert out["required"] == ["lineas_json"]
    desc = out["properties"]["lineas_json"]["description"]
    assert "sku" in desc and "cantidad" in desc


def test_array_de_escalares_se_conserva():
    out = sanear_para_odoo(
        {"properties": {"dias": {"type": "array", "items": {"type": "integer"}}}, "required": []}
    )
    assert out["properties"]["dias"]["items"] == {"type": "integer"}


def test_anidamiento_profundo_falla_explicito():
    """Mejor romper el build que emitir un esquema que Odoo va a rechazar."""
    entrada = {
        "properties": {
            "a": {"type": "object", "properties": {"b": {"type": "object", "properties": {}}}}
        },
        "required": [],
    }
    with pytest.raises(EsquemaNoTraducible):
        sanear_para_odoo(entrada)


def test_catalogo_completo_es_traducible():
    """Las 58 herramientas del catálogo real deben poder instalarse en Odoo."""
    data = json.loads(catalogo_path().read_text(encoding="utf-8"))
    defs = data.get("$defs", {})
    for agente, tools in data["herramientas"].items():
        for t in tools:
            out = sanear_para_odoo(t.get("input_schema", {}), defs)
            assert "required" in out, f"{agente}.{t['name']}"
            for nombre, prop in out["properties"].items():
                assert set(prop.keys()) <= CLAVES_PERMITIDAS_PROPIEDAD, (
                    f"{agente}.{t['name']}.{nombre}"
                )
                if prop["type"] == "array":
                    assert prop["items"]["type"] != "object", f"{agente}.{t['name']}.{nombre}"
