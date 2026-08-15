"""Verifica que el generador produce un esqueleto por herramienta del catálogo
y que TODOS llevan la guarda de llave (invariante: sin llave no hay ejecución)."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from generador import generar

CATALOGO = (
    pathlib.Path(__file__).resolve().parents[2]
    / "Agentes_SAAS" / "agentes_v2" / "herramientas" / "herramientas_esquemas.json"
)


def test_genera_todas_con_guarda(tmp_path):
    data = json.loads(CATALOGO.read_text(encoding="utf-8"))
    esperadas = sum(len(v) for v in data["herramientas"].values())
    n = generar(CATALOGO, tmp_path)
    assert n == esperadas  # hoy: 49
    generados = list(tmp_path.rglob("*.py"))
    assert len(generados) == esperadas
    for f in generados:
        assert "GUARDA BOOSTER" in f.read_text(encoding="utf-8"), f.name
