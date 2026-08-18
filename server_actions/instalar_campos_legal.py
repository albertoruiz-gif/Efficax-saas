"""Instalador one-shot (RPC directo, NO Server Action) de los campos
custom que el agente de Legal & Contratos necesita en
`documents.document` y que Odoo no tiene de forma nativa: un contrato
registrado necesita poder CONSULTARSE después (`alerta_vencimiento`
recibe solo `contrato_id` + `dias_antes` -- tiene que leer la vigencia
desde el propio registro, no le llega como parámetro).

Mismo patrón que `instalar_campos_inventarios.py`: se corre UNA VEZ vía
RPC directo (no dentro del sandbox de una Server Action). Idempotente.

Campos creados:
- `x_contrato_contraparte` (char)
- `x_contrato_vigencia_desde` (date)
- `x_contrato_vigencia_hasta` (date)
- `x_contrato_renovacion_automatica` (boolean)
- `x_contrato_dias_aviso_previo` (integer)
- `x_contrato_semaforo` (selection: verde/amarillo/rojo)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from booster_rpc import Odoo  # noqa: E402

CAMPOS = [
    {"name": "x_contrato_contraparte", "field_description": "Contraparte del contrato", "ttype": "char"},
    {"name": "x_contrato_vigencia_desde", "field_description": "Vigencia desde", "ttype": "date"},
    {"name": "x_contrato_vigencia_hasta", "field_description": "Vigencia hasta", "ttype": "date"},
    {"name": "x_contrato_renovacion_automatica", "field_description": "Renovacion automatica", "ttype": "boolean"},
    {"name": "x_contrato_dias_aviso_previo", "field_description": "Dias de aviso previo", "ttype": "integer"},
    {"name": "x_contrato_semaforo", "field_description": "Semaforo del contrato", "ttype": "selection",
     "selection": "[('verde','Verde'),('amarillo','Amarillo'),('rojo','Rojo')]"},
]


def instalar(o: Odoo) -> None:
    modelo_id = o.execute("ir.model", "search", [("model", "=", "documents.document")])[0]
    for campo in CAMPOS:
        existe = o.execute("ir.model.fields", "search", [
            ("model", "=", "documents.document"), ("name", "=", campo["name"]),
        ])
        if not existe:
            o.execute("ir.model.fields", "create", {**campo, "model_id": modelo_id})
            print(campo["name"], "creado")
        else:
            print(campo["name"], "ya existia")


if __name__ == "__main__":
    instalar(Odoo())
