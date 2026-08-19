"""Plan de contingencia de proveedor LLM — instalador del cron automatico.

Complementa a `scripts/conmutar_modelo.py` (interruptor manual). Este
script instala en el tenant un `ir.cron` (Acciones Planificadas) que cada
N minutos detecta si el proveedor primario esta caido y, de ser asi,
conmuta los agentes de Efficax al proveedor de respaldo -- y avisa. Idea
de Alberto (18-ago-2026): "el sistema deberia poder cambiar de modelo,
por ejemplo Gemini, que guarde el nombre del Cliente para que no pierda
familiaridad". La identidad vive en `ai.agent` (nombre, system_prompt,
temas), no en el modelo -- asi que conmutar `llm_model` conserva todo.

## Como detecta la caida (sin salir del sandbox)

El sandbox de un `ir.cron` no puede importar `requests` ni el cliente
LLM, asi que no puede hacer un ping directo a OpenAI. Lo que SI puede es
leer el sintoma en la base: cuando el proveedor cae, los mensajes de
humanos en canales `ai_chat` se quedan SIN respuesta del agente. Cada
agente tiene un `partner_id`; un mensaje humano cuyo ultimo mensaje
posterior en el canal NO es del partner del agente y ya tiene mas de
`MINUTOS_SIN_RESPUESTA` es una senal de caida. Verificado el 18-ago-2026
que todos esos campos son legibles (a diferencia de
`discuss.channel.ai_agent_id`, que esta restringido).

Umbral: hacen falta al menos `MIN_CANALES_AFECTADOS` canales distintos
sin respuesta para conmutar -- un solo chat colgado puede ser un timeout
aislado, no una caida del proveedor.

## Que hace cuando detecta

1. Cambia `llm_model` de los agentes de Efficax al perfil de respaldo.
2. Deja un `mail.activity` al dueno (usuario admin) diciendo que se
   conmuto, para que sepa que esta en respaldo y decida cuando volver.
3. NO vuelve solo al primario: la vuelta es decision humana con
   `scripts/conmutar_modelo.py openai` (evita ping-pong si el primario
   esta intermitente). Mientras esta en respaldo, el cron no hace nada
   mas que seguir vigilando.

## Prerrequisito de compatibilidad (encontrado en la prueba en vivo)

Gemini rechaza herramientas con `enum` numerico -- un solo enum asi y el
agente entero deja de responder bajo Gemini. Ya esta resuelto en
`esquemas_odoo.py` (los enums no-string se trasladan a la descripcion) y
protegido por `test_catalogo_completo_es_compatible_con_gemini`. Cualquier
herramienta nueva pasa por ese saneador, asi que la contingencia se
mantiene valida.

Uso:
    python instalar_contingencia_llm.py           # instala/actualiza el cron (activo)
    python instalar_contingencia_llm.py --probar   # dispara el cron a mano una vez
    python instalar_contingencia_llm.py --apagar   # desactiva el cron
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from booster_rpc import Odoo  # noqa: E402
from guarda_llave import GUARDA_TEMPLATE  # noqa: E402

NOMBRE_CRON = "Efficax: contingencia de proveedor LLM"

CUERPO = '''
# --- Contingencia de proveedor LLM (ver instalar_contingencia_llm.py) ---
AGENTES_EFFICAX = ('Mentor Efficax (piloto)', 'Booster')
MODELO_PRIMARIO = 'gpt-5'
MODELO_RESPALDO = 'gemini-2.5-pro'
MINUTOS_SIN_RESPUESTA = 3
MIN_CANALES_AFECTADOS = 2

Agente = env['ai.agent']
agentes = Agente.search([('name', 'in', AGENTES_EFFICAX)])
partners_agentes = set(agentes.mapped('partner_id').ids)

# Si ya estamos en respaldo, solo vigilar (la vuelta al primario es humana).
ya_en_respaldo = agentes and all(a.llm_model == MODELO_RESPALDO for a in agentes)

if agentes and not ya_en_respaldo:
    limite = datetime.datetime.now() - datetime.timedelta(minutes=MINUTOS_SIN_RESPUESTA)
    canales = env['discuss.channel'].search([('channel_type', '=', 'ai_chat')])
    afectados = []
    for canal in canales:
        ultimo = env['mail.message'].search([
            ('model', '=', 'discuss.channel'), ('res_id', '=', canal.id),
            ('message_type', '=', 'comment'),
        ], order='date desc', limit=1)
        if not ultimo:
            continue
        es_humano = ultimo.author_id.id not in partners_agentes
        if es_humano and ultimo.date < limite:
            afectados.append(canal.id)

    if len(afectados) >= MIN_CANALES_AFECTADOS:
        agentes.write({'llm_model': MODELO_RESPALDO})
        # La actividad se cuelga del partner del dueno, no del ai.agent:
        # ai.agent NO tiene mail.thread (sin message_subscribe -> el
        # create de mail.activity revienta). Confirmado en vivo 18-ago-2026.
        admin = env.ref('base.user_admin')
        env['mail.activity'].create({
            'res_model_id': env['ir.model']._get_id('res.partner'),
            'res_id': admin.partner_id.id,
            'activity_type_id': env.ref('mail.mail_activity_data_todo').id,
            'user_id': admin.id,
            'summary': 'Contingencia LLM: agentes conmutados a ' + MODELO_RESPALDO,
            'note': (
                'Se detectaron ' + str(len(afectados)) + ' conversaciones sin respuesta '
                'del agente por mas de ' + str(MINUTOS_SIN_RESPUESTA) + ' minutos (canales '
                + str(afectados) + '). Los agentes ' + ', '.join(AGENTES_EFFICAX) +
                ' fueron conmutados de ' + MODELO_PRIMARIO + ' a ' + MODELO_RESPALDO +
                '. La identidad (nombre, prompt, herramientas) se conserva. Para volver al '
                'primario cuando se restablezca: scripts/conmutar_modelo.py openai'
            ),
            'date_deadline': datetime.date.today(),
        })
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO


def instalar(o: Odoo, activo: bool = True) -> int:
    model_id = o.execute("ir.model", "search", [("model", "=", "ai.agent")])[0]
    valores = {
        "name": NOMBRE_CRON,
        "model_id": model_id,
        "state": "code",
        "code": CODIGO,
        "interval_number": 2,
        "interval_type": "minutes",
        "active": activo,
        "user_id": 1,  # OdooBot / admin tecnico
    }
    existentes = o.execute("ir.cron", "search", [("name", "=", NOMBRE_CRON)], context={"active_test": False})
    if existentes:
        o.execute("ir.cron", "write", existentes, valores)
        return existentes[0]
    return o.execute("ir.cron", "create", valores)


def main(argv: list[str]) -> int:
    o = Odoo()
    if "--apagar" in argv:
        ids = o.execute("ir.cron", "search", [("name", "=", NOMBRE_CRON)], context={"active_test": False})
        if ids:
            o.execute("ir.cron", "write", ids, {"active": False})
        print("cron desactivado:", ids)
        return 0
    cid = instalar(o, activo=True)
    print("cron instalado/actualizado id", cid, "(cada 2 min, activo)")
    if "--probar" in argv:
        o.execute("ir.cron", "method_direct_trigger", [cid])
        print("cron disparado a mano una vez")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
