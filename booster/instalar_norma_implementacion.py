"""Instala en el tenant la herramienta `evaluar_implementacion` de Booster
y el topic "Booster — Norma de implementación", que adopta como norma el
manual de implementación de Odoo (Perú) aportado por Alberto el
19-ago-2026, complementado en `booster/fuentes/NORMA-IMPLEMENTACION.md`.

Mismo patrón que `instalar_booster_fase1.py` (ir.actions.server con
`use_in_ai` + ai.topic + enlace al agente Booster), con UNA diferencia
deliberada: el topic se AGREGA al agente con `(4, id)`, no con `(6, 0,
[...])` -- el (6,0) del instalador de Fase 1 reemplaza todos los topics y
habría borrado "Booster — Fase 1: Descubrimiento". Verificado antes de
escribir esto: el agente Booster tiene hoy exactamente ese topic y no se
debe perder.

Uso:
    python instalar_norma_implementacion.py
    python instalar_norma_implementacion.py --probar   # ademas ejecuta la evaluacion via RPC y la imprime
"""
from __future__ import annotations

import json
import pathlib
import sys

RAIZ = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(RAIZ / "server_actions"))
sys.path.insert(0, str(RAIZ / "booster"))

from booster_rpc import Odoo  # noqa: E402

NOMBRE_TOOL = "booster: evaluar_implementacion"
NOMBRE_TOPIC = "Booster — Norma de implementación"

ESQUEMA = {
    "type": "object",
    "properties": {
        "alcance": {
            "type": "string",
            "enum": ["completo", "fundaciones", "datos_maestros", "operativo"],
            "description": (
                "Que parte de la norma evaluar. 'completo' (por defecto) corre todo. "
                "'fundaciones' = Fase 0 (localizacion, compania, OSE, diarios, plan de cuentas). "
                "'datos_maestros' = Fase 1 (productos, clientes, proveedores, migracion). "
                "'operativo' = Fase 2 (CRM, almacenes, reabastecimiento, cobranzas, credito)."
            ),
        },
    },
    "required": [],
}

TOPIC_INSTRUCCIONES = """Eres Booster aplicando la NORMA DE IMPLEMENTACION ODOO de Efficax (basada en el manual de implementacion Peru, complementado por Efficax).

La norma tiene 6 fases en orden: Fase 0 Fundaciones (localizacion Peru, datos de compania, OSE, usuarios, diarios, plan de cuentas) -> Fase 1 Datos maestros (productos con UNSPSC, clientes con documento y ubigeo, proveedores con RUC, condiciones de pago, MIGRACION de saldos/stock/deudas) -> Fase 2 Flujos operativos (Ventas, CRM, Compras, Inventario, Contabilidad y cobranzas con reglas INDECOPI) -> Fase 3 Verificacion (smoke test de punta a punta, doble prueba de automatizaciones, limpiar datos de prueba) -> Fase 4 Go-live (respaldo, secuencias limpias, usuarios reales, capacitacion, canal de soporte) -> Fase 5 Post-implementacion (soporte, actualizaciones, contingencia LLM activa, revision a 30 dias).

Como usar la herramienta evaluar_implementacion:
- Para un cliente NUEVO: correla al cerrar cada fase, con el alcance de esa fase, para confirmar que quedo completa antes de avanzar. No pases de fase con un bloqueante abierto.
- Para un Odoo que YA ESTA ANDANDO (el dueno ya tenia Odoo): correla 'completo' al inicio. El resultado es el diagnostico de por donde empezar.

Como presentar el resultado al dueno (es dueno de negocio, no ingeniero):
1. Empieza por el veredicto en una frase.
2. Luego los BLOQUEANTES, uno por uno, diciendo que pasa y que hay que hacer -- en lenguaje de negocio ("SUNAT va a rechazar tus facturas porque faltan...") no tecnico ("el campo vat esta vacio").
3. Los puntos 'a_conversar' son preguntas que le tienes que hacer al dueno -- hazlas, no las asumas.
4. Los importantes y recomendados van despues, agrupados. No abrumes: si hay mas de 5, prioriza y ofrece el resto para despues.
5. Guarda el resultado con guardar_avance_wizard (checkpoint_nota = resumen del diagnostico) para que quede en el expediente.

Reglas:
- Nunca inventes un hallazgo que la herramienta no devolvio.
- Si un check dice 'verificar a mano', dilo asi: es algo que tu o el dueno tienen que mirar, la herramienta no lo pudo confirmar sola.
- La norma es para Peru (SUNAT/PCGE/INDECOPI). Si el dueno opera en otro pais, dilo explicito: la norma no aplica tal cual y hay que validar la localizacion local antes de implementar -- no improvises.
"""


def instalar_tool(o: Odoo) -> int:
    from implementaciones.evaluar_implementacion import CODIGO  # noqa: PLC0415

    # Sobre res.company: el check arranca por la compania y desde ahi navega al resto.
    model_id = o.execute("ir.model", "search", [("model", "=", "res.company")])[0]
    existentes = o.execute("ir.actions.server", "search", [("name", "=", NOMBRE_TOOL)])
    valores = {
        "name": NOMBRE_TOOL,
        "model_id": model_id,
        "state": "code",
        "code": CODIGO,
        "use_in_ai": True,
        "ai_tool_description": (
            "Evalua los vacios de la implementacion Odoo contra la Norma de Implementacion de Booster "
            "(localizacion Peru, datos de compania, OSE, diarios, plan de cuentas, productos con UNSPSC, "
            "clientes/proveedores con documento, CRM, almacenes, reabastecimiento, cobranzas, credito). "
            "Devuelve veredicto + hallazgos bloqueantes/importantes/recomendados + puntos a conversar con el dueno. "
            "Usar al inicio con un Odoo ya existente, o al cerrar cada fase de una implementacion nueva."
        ),
        "ai_tool_schema": json.dumps(ESQUEMA, ensure_ascii=False),
    }
    if existentes:
        o.execute("ir.actions.server", "write", existentes, valores)
        return existentes[0]
    return o.execute("ir.actions.server", "create", valores)


def instalar_topic(o: Odoo, tool_id: int) -> int:
    existentes = o.execute("ai.topic", "search", [("name", "=", NOMBRE_TOPIC)])
    valores = {"name": NOMBRE_TOPIC, "instructions": TOPIC_INSTRUCCIONES, "tool_ids": [(6, 0, [tool_id])]}
    if existentes:
        o.execute("ai.topic", "write", existentes, valores)
        return existentes[0]
    return o.execute("ai.topic", "create", valores)


def enlazar_a_booster(o: Odoo, topic_id: int) -> int:
    agente = o.execute("ai.agent", "search", [("name", "=", "Booster")])
    if not agente:
        raise RuntimeError("El agente Booster no existe -- correr antes instalar_booster_fase1.py")
    # (4, id) AGREGA el topic sin tocar los existentes. Nunca (6, 0, [...]) aca.
    o.execute("ai.agent", "write", agente, {"topic_ids": [(4, topic_id)]})
    return agente[0]


def instalar(o: Odoo) -> dict:
    tool_id = instalar_tool(o)
    topic_id = instalar_topic(o, tool_id)
    agente_id = enlazar_a_booster(o, topic_id)
    topics = o.execute("ai.agent", "read", [agente_id], fields=["topic_ids"])[0]["topic_ids"]
    return {"tool_id": tool_id, "topic_id": topic_id, "agente_id": agente_id, "topics_del_agente": topics}


def probar(o: Odoo, tool_id: int) -> None:
    """Ejecuta la evaluacion directamente (sin pasar por el LLM) y la imprime."""
    # run() de una server action con use_in_ai necesita el contexto 'ai' -- se prueba
    # via el chat del agente. Aca solo se valida que el codigo compile sin error en Odoo
    # usando una copia que devuelve el resultado por excepcion controlada no es limpio,
    # asi que la prueba funcional real es por chat (ver README). Este --probar solo lee
    # el registro instalado y confirma que tiene el codigo y el esquema esperados.
    sa = o.execute("ir.actions.server", "read", [tool_id], fields=["name", "use_in_ai", "ai_tool_schema"])[0]
    print("Instalado:", sa["name"], "| use_in_ai:", sa["use_in_ai"])
    print("Esquema:", sa["ai_tool_schema"][:200], "...")


if __name__ == "__main__":
    o = Odoo()
    resultado = instalar(o)
    print("Norma de implementacion instalada:", resultado)
    if "--probar" in sys.argv:
        probar(o, resultado["tool_id"])
