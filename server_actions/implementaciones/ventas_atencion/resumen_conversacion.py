"""Server Action: ventas_atencion / resumen_conversacion

Sexta herramienta con lógica real. A diferencia de `derivar_humano`, acá
`lead_id` SÍ es obligatorio en el esquema — tiene sentido: no existe
"resumen de conversación" sin una conversación/lead concreto al cual
escribirle el chatter. Por eso, a diferencia de `derivar_humano`, no hay
fallback: si el lead no existe (o no es visible con los permisos reales
del usuario), se devuelve `ok=false` en vez de inventar un destino.

Solo escribe al chatter (`message_post`) — la descripción del catálogo
("escribe el resumen al chatter") no pide agendar ninguna actividad de
seguimiento, así que no se agrega una que el catálogo no pidió.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
resumen_txt = (resumen or '').strip()
proxima = (proxima_accion or '').strip()
canal_val = (canal or 'livechat').strip()

if not lead_id:
    ai['result'] = {'ok': False, 'mensaje': 'Necesito el lead_id de la conversacion para registrar el resumen.', 'datos': {}}
elif len(resumen_txt) < 30:
    # minLength no lo valida Odoo (ver esquemas_odoo.py) -- se valida acá.
    ai['result'] = {'ok': False, 'mensaje': 'El resumen es muy corto: necesito al menos 30 caracteres de contexto real.', 'datos': {}}
else:
    lead = env['crm.lead'].browse(int(lead_id)).exists()
    if not lead:
        ai['result'] = {'ok': False, 'mensaje': 'No encontre ningun lead con ese id.', 'datos': {}}
    else:
        cuerpo_msg = 'Resumen de conversacion (' + canal_val + '): ' + resumen_txt
        if proxima:
            cuerpo_msg += '\\n\\nProxima accion: ' + proxima
        lead.message_post(body=cuerpo_msg)
        ai['result'] = {
            'ok': True,
            'mensaje': 'Resumen registrado en el lead.',
            'datos': {'lead_id': lead.id, 'canal': canal_val},
        }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
