"""Invariantes sobre las implementaciones REALES (no los esqueletos del
generador): cada `.py` en `implementaciones/<agente>/` expone un CODIGO que
1) empieza con la guarda de licencia, 2) no usa sudo() fuera de la guarda,
3) si toca datetime lo hace con datetime.datetime.now() (nunca
datetime.now(), que no existe en el sandbox de Odoo — ver guarda_llave.py),
y 4) corresponde a una herramienta que sigue existiendo en el catálogo.

Corre sobre lo que haya en implementaciones/ en cada momento: crece solo a
medida que se agregan herramientas, sin tocar este archivo.
"""
import importlib
import json
import pathlib
import re
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from generador import catalogo_path  # noqa: E402
from guarda_llave import BUILTINS_NO_DISPONIBLES, GUARDA_TEMPLATE  # noqa: E402

IMPLEMENTACIONES_DIR = pathlib.Path(__file__).parent / "implementaciones"


def _modulos_implementados():
    """(agente, nombre, modulo_import_path) por cada .py real bajo implementaciones/."""
    encontrados = []
    for archivo in sorted(IMPLEMENTACIONES_DIR.glob("*/*.py")):
        agente = archivo.parent.name
        nombre = archivo.stem
        encontrados.append((agente, nombre, f"implementaciones.{agente}.{nombre}"))
    return encontrados


MODULOS = _modulos_implementados()
IDS = [f"{agente}/{nombre}" for agente, nombre, _ in MODULOS]


def test_hay_al_menos_una_implementacion():
    assert MODULOS, "No se encontró ninguna implementación real bajo implementaciones/"


@pytest.mark.parametrize("agente,nombre,modpath", MODULOS, ids=IDS)
def test_codigo_empieza_con_la_guarda(agente, nombre, modpath):
    mod = importlib.import_module(modpath)
    assert mod.CODIGO.startswith(GUARDA_TEMPLATE), (
        f"{nombre}: la guarda debe ir siempre primero en CODIGO"
    )


@pytest.mark.parametrize("agente,nombre,modpath", MODULOS, ids=IDS)
def test_sin_sudo_fuera_de_la_guarda(agente, nombre, modpath):
    mod = importlib.import_module(modpath)
    cuerpo = mod.CODIGO.replace(GUARDA_TEMPLATE, "", 1)
    assert "sudo()" not in cuerpo, f"{nombre}: sudo() fuera de la guarda"


@pytest.mark.parametrize("agente,nombre,modpath", MODULOS, ids=IDS)
def test_datetime_now_siempre_calificado(agente, nombre, modpath):
    """`datetime.now()` (sin el módulo dos veces) rompe en el sandbox de Odoo
    -- ver guarda_llave.py. Cualquier uso de datetime.now debe ser
    datetime.datetime.now."""
    mod = importlib.import_module(modpath)
    for m in re.finditer(r"(?<!datetime\.)\bdatetime\.now\(", mod.CODIGO):
        pytest.fail(f"{nombre}: usa datetime.now() sin calificar en '...{mod.CODIGO[max(0, m.start()-20):m.start()+20]}...'")


CLASES_DE_EXCEPCION_NO_DISPONIBLES = (
    "ValueError", "TypeError", "KeyError", "AttributeError", "IndexError",
    "RuntimeError", "NameError", "Exception", "StopIteration",
)


@pytest.mark.parametrize("agente,nombre,modpath", MODULOS, ids=IDS)
def test_sin_clases_de_excepcion_no_disponibles(agente, nombre, modpath):
    """`except ValueError:` (y similares) revienta con NameError real en el
    sandbox de Odoo -- esas clases no estan expuestas ahi (detectado en vivo
    en agendar_reunion.py: un parseo de fecha con try/except ValueError
    fallo con "name 'ValueError' is not defined"). Usar `except:` desnudo."""
    mod = importlib.import_module(modpath)
    for clase in CLASES_DE_EXCEPCION_NO_DISPONIBLES:
        assert f"except {clase}" not in mod.CODIGO, (
            f"{nombre}: 'except {clase}' no funciona en el sandbox de Odoo -- usar 'except:' desnudo"
        )


@pytest.mark.parametrize("agente,nombre,modpath", MODULOS, ids=IDS)
def test_tool_sigue_en_el_catalogo(agente, nombre, modpath):
    data = json.loads(catalogo_path().read_text(encoding="utf-8"))
    nombres_catalogo = {t["name"] for t in data["herramientas"].get(agente, [])}
    assert nombre in nombres_catalogo, (
        f"{agente}/{nombre}: implementado pero ya no está en el catálogo (¿se renombró?)"
    )


@pytest.mark.parametrize("agente,nombre,modpath", MODULOS, ids=IDS)
def test_sin_builtins_no_disponibles(agente, nombre, modpath):
    """`getattr`, `type`, etc. no existen en el sandbox de Odoo -- lanzan
    NameError recien en vivo (getattr detectado el 19-ago-2026 en
    booster/evaluar_implementacion; `type` ya estaba documentado en
    guarda_llave.py pero ningun test lo hacia cumplir). Usar
    `'campo' in rec._fields` + acceso directo en lugar de getattr."""
    mod = importlib.import_module(modpath)
    cuerpo = mod.CODIGO.replace(GUARDA_TEMPLATE, "", 1)
    for builtin in BUILTINS_NO_DISPONIBLES:
        for m in re.finditer(rf"(?<![\w.]){builtin}\(", cuerpo):
            pytest.fail(
                f"{agente}/{nombre}: usa '{builtin}(' que no existe en el sandbox de Odoo "
                f"('...{cuerpo[max(0, m.start()-25):m.start()+30]}...')"
            )
