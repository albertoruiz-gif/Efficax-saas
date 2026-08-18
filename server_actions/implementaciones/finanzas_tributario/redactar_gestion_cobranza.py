"""Server Action: finanzas_tributario / redactar_gestion_cobranza

Redacta el mensaje de cobranza según el tono real de
`Playbook_Creditos_Cobranzas.md` §4 por tramo (Servicio/Cordial/Firme y
claro/Formal/Severo/Legal) y registra la gestión en el chatter de la
factura (`message_post` -- `account.move` hereda `mail.thread`).
`aprobacion: "dueno"` -- el catálogo es explícito: **queda como
BORRADOR** salvo que el tramo esté pre-aprobado (decisión de Fase 4, que
todavía no existe en este tenant) -- por eso esta herramienta NUNCA
envía nada por su cuenta, solo redacta y deja constancia de que se
redactó un borrador. Enviarlo de verdad (email/whatsapp/carta) es una
acción humana fuera de esta herramienta.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
TRAMOS_VALIDOS = ('preventiva', 'temprana', 'intermedia_1', 'intermedia_2', 'tardia', 'prejudicial')
CANALES_VALIDOS = ('email', 'whatsapp', 'carta')

TONO_Y_PROPOSITO = {
    'preventiva': ('Servicio, no cobranza', 'Confirmar recepcion de la factura y su conformidad; recordar fecha, monto y medios de pago disponibles.'),
    'temprana': ('Cordial', 'Recordatorio amable de que la factura vencio hace pocos dias; pedir que confirme el motivo si hay algun atraso.'),
    'intermedia_1': ('Firme y claro', 'Pedir un compromiso de pago con fecha concreta; ofrecer coordinar con el responsable de pago.'),
    'intermedia_2': ('Formal', 'Comunicacion formal de cobranza; mencionar que de continuar el atraso podria generar intereses por demora.'),
    'tardia': ('Severo', 'Aviso de que la cuenta pasa a condicion de solo contado hasta regularizar; se advierte sobre gestiones adicionales de cobranza.'),
    'prejudicial': ('Legal', 'Aviso prejudicial: se esta evaluando el expediente de la deuda para una posible accion legal si no se regulariza.'),
}

tramo_txt = (tramo or '').strip()
canal_txt = (canal or '').strip()

Move = env['account.move']
factura = Move.browse(factura_id) if factura_id else Move.browse()

errores = []
if not factura.exists():
    errores.append('no encontre ninguna factura con id ' + str(factura_id))
elif factura.move_type not in ('out_invoice', 'out_refund'):
    errores.append('la factura ' + str(factura_id) + ' no es una factura de cliente')
if tramo_txt not in TRAMOS_VALIDOS:
    errores.append('tramo debe ser una de: ' + ', '.join(TRAMOS_VALIDOS))
if canal_txt not in CANALES_VALIDOS:
    errores.append('canal debe ser email, whatsapp o carta')

if errores:
    ai['result'] = {'ok': False, 'mensaje': 'No pude redactar la gestion: ' + '; '.join(errores) + '.', 'datos': {}}
else:
    tono_txt, proposito_txt = TONO_Y_PROPOSITO[tramo_txt]
    cliente_nombre = factura.partner_id.name if factura.partner_id else 'el cliente'

    borrador = (
        'Estimado/a ' + cliente_nombre + ',\\n\\n' +
        proposito_txt + '\\n\\n' +
        'Factura: ' + factura.name + ' -- Monto pendiente: ' + str(factura.amount_residual) +
        (' ' + factura.currency_id.name if factura.currency_id else '') +
        ' -- Vencimiento: ' + (str(factura.invoice_date_due) if factura.invoice_date_due else 'sin fecha') + '\\n\\n' +
        'Quedamos atentos.'
    )

    nota_registro = (
        'Gestion de cobranza BORRADOR (tramo: ' + tramo_txt + ', tono: ' + tono_txt + ', canal: ' + canal_txt + '). ' +
        'NO enviado -- queda pendiente de aprobacion y envio manual del dueno.\\n\\n' + borrador
    )
    factura.message_post(body=nota_registro)

    ai['result'] = {
        'ok': True,
        'mensaje': 'Borrador de cobranza (' + tramo_txt + ', tono ' + tono_txt + ', canal ' + canal_txt + ') redactado y registrado en el chatter de ' + factura.name + '. NO se envio -- necesita tu aprobacion y envio manual.',
        'datos': {'factura_id': factura.id, 'tramo': tramo_txt, 'canal': canal_txt, 'tono': tono_txt, 'borrador': borrador},
    }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
