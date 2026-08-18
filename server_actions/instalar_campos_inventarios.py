"""Instalador one-shot (RPC directo, NO Server Action) de los 2 campos
custom que el agente de Inventarios necesita en `product.template` y que
Odoo no tiene de forma nativa:

- `x_clase_abc` (selection A/B/C): clasificación ABC del SKU. Sin esto,
  `clasificar_abc.py` no tendría dónde persistir el resultado -- tendría
  que recalcularlo desde cero en cada llamada, y el resto de
  herramientas del agente (`generar_plan_conteo`, `entregar_conteo_dia`,
  `alerta_quiebre_exceso`) necesitan leer una clasificación YA fijada,
  no recalculada sobre la marcha cada vez (Odoo no expone ninguna
  clasificación ABC nativa -- confirmado con `fields_get`).
- `x_proximo_conteo_ciclico` (date): próxima fecha programada de conteo
  cíclico para ese SKU, que arma `generar_plan_conteo.py` y consume
  `entregar_conteo_dia.py`.

Mismo patrón que usó Booster para sus propios campos/modelos: se corre
UNA VEZ vía RPC directo (no dentro del sandbox de una Server Action,
donde crear campos dinámicamente en la misma transacción no es
confiable -- ver `implementaciones/README.md`). Idempotente: correrlo de
nuevo no falla ni duplica nada.

El ajuste de cantidades en sí (`ajustar_inventario.py`) NO necesita
ningún campo nuevo: usa el mecanismo nativo real de Odoo
(`stock.quant.inventory_quantity` + `action_apply_inventory()`,
confirmado que existe y ejecuta con una llamada RPC real) -- no hay que
inventar nada ahí.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from booster_rpc import Odoo  # noqa: E402


def instalar(o: Odoo) -> None:
    Fields = o.execute("ir.model.fields", "search", [
        ("model", "=", "product.template"), ("name", "=", "x_clase_abc"),
    ])
    if not Fields:
        modelo_id = o.execute("ir.model", "search", [("model", "=", "product.template")])[0]
        o.execute("ir.model.fields", "create", {
            "model_id": modelo_id,
            "name": "x_clase_abc",
            "field_description": "Clase ABC (inventarios)",
            "ttype": "selection",
            "selection": "[('A','A'),('B','B'),('C','C')]",
        })
        print("x_clase_abc creado")
    else:
        print("x_clase_abc ya existia")

    Fields2 = o.execute("ir.model.fields", "search", [
        ("model", "=", "product.template"), ("name", "=", "x_proximo_conteo_ciclico"),
    ])
    if not Fields2:
        modelo_id = o.execute("ir.model", "search", [("model", "=", "product.template")])[0]
        o.execute("ir.model.fields", "create", {
            "model_id": modelo_id,
            "name": "x_proximo_conteo_ciclico",
            "field_description": "Proximo conteo ciclico (inventarios)",
            "ttype": "date",
        })
        print("x_proximo_conteo_ciclico creado")
    else:
        print("x_proximo_conteo_ciclico ya existia")


if __name__ == "__main__":
    instalar(Odoo())
