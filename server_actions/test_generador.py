"""Verifica que el generador produce un artefacto por herramienta del catálogo:
JSON de payload ir.actions.server para las que ejecutan en Odoo, esqueleto .py
para las que ejecutan en el Servidor de Control. Invariante: sin llave no hay
ejecución (la guarda aparece en TODO payload de ir.actions.server) y ninguna
herramienta usa sudo() salvo la guarda misma."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from generador import catalogo_path, generar

CATALOGO = catalogo_path()


def test_catalogo_existe():
    assert CATALOGO.exists(), f"Catálogo no encontrado en {CATALOGO} — ver EFFICAX_CATALOGO"


def test_genera_todas_con_guarda_y_sin_sudo_indebido(tmp_path):
    data = json.loads(CATALOGO.read_text(encoding="utf-8"))
    esperadas = sum(len(v) for v in data["herramientas"].values())
    resumen = generar(CATALOGO, tmp_path)
    assert resumen["total"] == esperadas  # hoy: 58

    generados_json = list(tmp_path.rglob("*.json"))
    generados_py = list(tmp_path.rglob("*.py"))
    assert len(generados_json) == resumen["ir_actions_server"]
    assert len(generados_py) == resumen["servidor_control"]
    assert len(generados_json) + len(generados_py) == esperadas

    for f in generados_json:
        payload = json.loads(f.read_text(encoding="utf-8"))
        assert "GUARDA BOOSTER" in payload["code"], f.name
        assert "sudo()" not in payload["code"].replace(
            "lic = env['x_booster_licencia'].sudo()", ""
        ), f"{f.name}: sudo() fuera de la guarda"
        assert payload["use_in_ai"] is True
        assert payload["ai_tool_description"]
        json.loads(payload["ai_tool_schema"])  # debe ser JSON válido embebido

    for f in generados_py:
        assert "GENERADO desde herramientas_esquemas.json" in f.read_text(encoding="utf-8")


def test_incluye_agente_inventarios(tmp_path):
    data = json.loads(CATALOGO.read_text(encoding="utf-8"))
    assert "inventarios" in data["herramientas"], "Falta el agente inventarios en el catálogo"
    generar(CATALOGO, tmp_path)
    assert (tmp_path / "inventarios").exists()
