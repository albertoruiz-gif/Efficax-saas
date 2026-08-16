"""Invariantes sobre las implementaciones reales de Booster (mismo espíritu
que `server_actions/test_implementaciones.py`, pero sin el chequeo contra
`herramientas_esquemas.json`: Booster no es una herramienta del catálogo de
agentes de cara al cliente, es el implementador — no tiene entrada ahí)."""
import importlib
import pathlib
import re
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "server_actions"))

from guarda_llave import GUARDA_TEMPLATE  # noqa: E402

IMPLEMENTACIONES_DIR = pathlib.Path(__file__).parent / "implementaciones"


def _modulos_implementados():
    return [
        (archivo.stem, f"implementaciones.{archivo.stem}")
        for archivo in sorted(IMPLEMENTACIONES_DIR.glob("*.py"))
    ]


MODULOS = _modulos_implementados()
IDS = [nombre for nombre, _ in MODULOS]

CLASES_DE_EXCEPCION_NO_DISPONIBLES = (
    "ValueError", "TypeError", "KeyError", "AttributeError", "IndexError",
    "RuntimeError", "NameError", "Exception", "StopIteration",
)


def test_hay_al_menos_una_implementacion():
    assert MODULOS, "No se encontró ninguna implementación real bajo booster/implementaciones/"


@pytest.mark.parametrize("nombre,modpath", MODULOS, ids=IDS)
def test_codigo_empieza_con_la_guarda(nombre, modpath):
    mod = importlib.import_module(modpath)
    assert mod.CODIGO.startswith(GUARDA_TEMPLATE), f"{nombre}: la guarda debe ir siempre primero en CODIGO"


@pytest.mark.parametrize("nombre,modpath", MODULOS, ids=IDS)
def test_sin_sudo_fuera_de_la_guarda(nombre, modpath):
    mod = importlib.import_module(modpath)
    cuerpo = mod.CODIGO.replace(GUARDA_TEMPLATE, "", 1)
    assert "sudo()" not in cuerpo, f"{nombre}: sudo() fuera de la guarda"


@pytest.mark.parametrize("nombre,modpath", MODULOS, ids=IDS)
def test_datetime_now_siempre_calificado(nombre, modpath):
    mod = importlib.import_module(modpath)
    for m in re.finditer(r"(?<!datetime\.)\bdatetime\.now\(", mod.CODIGO):
        pytest.fail(f"{nombre}: usa datetime.now() sin calificar en '...{mod.CODIGO[max(0, m.start()-20):m.start()+20]}...'")


@pytest.mark.parametrize("nombre,modpath", MODULOS, ids=IDS)
def test_sin_clases_de_excepcion_no_disponibles(nombre, modpath):
    mod = importlib.import_module(modpath)
    for clase in CLASES_DE_EXCEPCION_NO_DISPONIBLES:
        assert f"except {clase}" not in mod.CODIGO, (
            f"{nombre}: 'except {clase}' no funciona en el sandbox de Odoo -- usar 'except:' desnudo"
        )
