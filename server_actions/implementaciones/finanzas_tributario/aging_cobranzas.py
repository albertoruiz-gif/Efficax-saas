"""Server Action: finanzas_tributario / aging_cobranzas

Solo lectura (`aprobacion: "ninguna"`). Cartera vencida por tramo, usando
la matriz REAL de `Playbook_Creditos_Cobranzas.md` §4 (7 tramos,
Motorex/Efficax, no inventada): Preventiva (no vencida todavía),
Temprana 1-7 días, Intermedia 1 7-15, Intermedia 2 15-30, Tardía 30-60,
Prejudicial 60-360, Judicial 360+. Cada fila trae la "acción del agente"
sugerida por el playbook para ese tramo -- texto, no una acción
ejecutada (esta herramienta no manda nada, solo informa).

`solo_vencidas` (default true, Odoo no soporta `default` -- se aplica a
mano) excluye el tramo Preventiva si está en true.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
def tramo_de(dias_vencido):
    if dias_vencido <= 0:
        return ('preventiva', 'Confirmar recepcion de factura y conformidad; recordar fecha, monto y medios de pago')
    if dias_vencido <= 7:
        return ('temprana', 'Recordatorio amable por correo/mensaje + registrar motivo del atraso')
    if dias_vencido <= 15:
        return ('intermedia_1', 'Llamada/mensaje directo al responsable de pago; proponer compromiso de pago con fecha')
    if dias_vencido <= 30:
        return ('intermedia_2', 'Carta de cobranza formal; aviso de intereses por demora si aplica')
    if dias_vencido <= 60:
        return ('tardia', 'Cliente pasa a solo contado (regla dura); carta notarial')
    if dias_vencido <= 360:
        return ('prejudicial', 'Expediente de deuda completo; evaluar costo/beneficio de accion legal')
    return ('judicial', 'Derivar a abogado externo con expediente listo; evaluar provision de incobrable')

solo_vencidas_val = True if solo_vencidas is None else bool(solo_vencidas)
cliente_txt = (cliente or '').strip()

Move = env['account.move']
dominio = [
    ('move_type', 'in', ('out_invoice', 'out_refund')),
    ('state', '=', 'posted'),
    ('payment_state', 'not in', ('paid', 'reversed')),
]
if cliente_txt:
    dominio.append(('partner_id.name', 'ilike', cliente_txt))

facturas = Move.search(dominio)
hoy = datetime.date.today()

filas = []
resumen = {}
for f in facturas:
    if not f.invoice_date_due:
        continue
    dias_vencido = (hoy - f.invoice_date_due).days
    tramo_txt, accion_txt = tramo_de(dias_vencido)
    if solo_vencidas_val and tramo_txt == 'preventiva':
        continue
    filas.append({
        'factura_id': f.id, 'factura': f.name,
        'cliente': f.partner_id.name if f.partner_id else False,
        'monto_pendiente': f.amount_residual, 'moneda': f.currency_id.name if f.currency_id else False,
        'vencimiento': str(f.invoice_date_due), 'dias_vencido': dias_vencido,
        'tramo': tramo_txt, 'accion_sugerida': accion_txt,
    })
    resumen[tramo_txt] = resumen.get(tramo_txt, 0) + f.amount_residual

filas.sort(key=lambda r: -r['dias_vencido'])

ai['result'] = {
    'ok': True,
    'mensaje': (
        'Cartera' + (' vencida' if solo_vencidas_val else '') + (' de "' + cliente_txt + '"' if cliente_txt else '') +
        ': ' + str(len(filas)) + ' factura(s). Por tramo: ' +
        '; '.join(t + ' = ' + str(m) for t, m in resumen.items()) if resumen else 'Sin facturas en cartera' + (' vencida' if solo_vencidas_val else '') + '.'
    ),
    'datos': {'solo_vencidas': solo_vencidas_val, 'cliente_filtro': cliente_txt or False, 'facturas': filas, 'resumen_por_tramo': resumen},
}
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
