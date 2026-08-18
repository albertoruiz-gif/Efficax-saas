"""Server Action: finanzas_tributario / evaluar_credito

`aprobacion: "confirmar"`. Scoring de 5 criterios (100 puntos) y matriz
de garantías tal como los define `Playbook_Creditos_Cobranzas.md` §3.2
y §3.3 -- NO es un scoring inventado. Es una PROPUESTA: el catálogo dice
explícito "aprueba el dueño según la escalera P2/P3/P4" -- esta
herramienta no otorga nada, no escribe `credit_limit` ni ningún campo,
solo calcula y recomienda.

**Parámetros P1-P12 del playbook:** en este tenant NO existe todavía
ningún registro de los valores que el dueño habría elegido en el
provisioning de Fase 3 (que no se ha corrido) -- se usan los
**"Default PYME"** de la tabla §2 del playbook (P2 = USD 1,000, P4 = USD
5,000) como punto de partida, declarado explícito en la respuesta. Si
`moneda` es PEN, se convierte a USD con `res.currency._convert` (API
nativa de Odoo, sin librerías externas) usando el tipo de cambio
vigente en Odoo para comparar contra esos umbrales en USD.

**Campos Studio del playbook** (`x_scoring`, `x_clase_cliente`,
`x_responsable_pago` en el contacto -- que Booster crearía en Fase 3
provisioning) **tampoco existen todavía** en este tenant (confirmado con
`fields_get`, no asumido) -- el scoring se calcula fresco cada vez desde
datos reales (historial de facturas, antigüedad del contacto, si tiene
teléfono/email) y NO se intenta persistir en campos que no existen.

Los 5 criterios y su cálculo real (aproximaciones documentadas, no
inventadas sin base):
- Historial de pago interno (30 pts): % de facturas pasadas ya cobradas
  (`payment_state='paid'`) sobre el total facturado al cliente.
- Antigüedad como cliente (15 pts): años desde su primera factura.
- Verificación de contacto (15 pts, proxy de "responsable de pago
  identificado" -- no hay campo dedicado): tiene teléfono Y email.
- Referencias/central de riesgo (25 pts): **0 fijo** -- no hay
  integración con una central de riesgos (Sentinel/Infocorp) en este
  tenant; declarado explícito, no inventado.
- Tamaño y frecuencia de compra (15 pts): cantidad de facturas pasadas.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
P2_USD = 1000.0
P4_USD = 5000.0

cliente_txt = (cliente or '').strip()
monto_val = monto_solicitado
moneda_txt = (moneda or 'PEN').strip()
plazo_val = plazo_dias

errores = []
if not cliente_txt:
    errores.append('falta el nombre del cliente')
if monto_val is None or monto_val <= 0:
    errores.append('monto_solicitado debe ser mayor a 0')
if moneda_txt not in ('PEN', 'USD'):
    errores.append('moneda debe ser PEN o USD')
if plazo_val not in (30, 45, 60):
    errores.append('plazo_dias debe ser 30, 45 o 60')

if errores:
    ai['result'] = {'ok': False, 'mensaje': 'No pude evaluar el credito: ' + '; '.join(errores) + '.', 'datos': {}}
else:
    Partner = env['res.partner'].search([('name', 'ilike', cliente_txt)], limit=5)
    if not Partner:
        ai['result'] = {'ok': False, 'mensaje': 'No encontre ningun cliente que coincida con "' + cliente_txt + '".', 'datos': {}}
    elif len(Partner) > 1:
        nombres = [p.name + ' (id ' + str(p.id) + ')' for p in Partner]
        ai['result'] = {'ok': False, 'mensaje': 'Hay varios clientes que coinciden con "' + cliente_txt + '". Precisa cual: ' + '; '.join(nombres), 'datos': {}}
    else:
        p = Partner
        Move = env['account.move']
        facturas = Move.search([('partner_id', '=', p.id), ('move_type', 'in', ('out_invoice', 'out_refund')), ('state', '=', 'posted')])
        total_facturas = len(facturas)
        pagadas = len(facturas.filtered(lambda m: m.payment_state == 'paid'))

        puntos_historial = (pagadas / total_facturas * 30) if total_facturas else 0.0
        primera_factura = min(facturas.mapped('invoice_date')) if facturas else False
        anios_antiguedad = ((datetime.date.today() - primera_factura).days / 365.0) if primera_factura else 0.0
        puntos_antiguedad = 15.0 if anios_antiguedad >= 2 else (10.0 if anios_antiguedad >= 1 else (5.0 if anios_antiguedad > 0 else 0.0))
        puntos_contacto = 15.0 if (p.phone and p.email) else (7.5 if (p.phone or p.email) else 0.0)
        puntos_referencias = 0.0  # sin integracion a central de riesgo -- ver docstring
        puntos_volumen = 15.0 if total_facturas >= 10 else (10.0 if total_facturas >= 5 else (5.0 if total_facturas >= 1 else 0.0))

        puntaje_total = puntos_historial + puntos_antiguedad + puntos_contacto + puntos_referencias + puntos_volumen

        if puntaje_total >= 90:
            riesgo_txt = 'sin_riesgo'
        elif puntaje_total >= 70:
            riesgo_txt = 'riesgo_medio'
        else:
            riesgo_txt = 'alto_riesgo'

        Moneda = env['res.currency'].search([('name', '=', moneda_txt)], limit=1)
        MonedaUSD = env['res.currency'].search([('name', '=', 'USD')], limit=1)
        if moneda_txt == 'USD' or not MonedaUSD:
            monto_usd = monto_val
        else:
            monto_usd = Moneda._convert(monto_val, MonedaUSD, env.company, datetime.date.today())

        if monto_usd <= P2_USD:
            tramo_monto = 'hasta_P2'
        elif monto_usd <= P4_USD:
            tramo_monto = 'P2_a_P4'
        else:
            tramo_monto = 'sobre_P4'

        MATRIZ_GARANTIA = {
            ('hasta_P2', 'sin_riesgo'): 'Factura simple',
            ('hasta_P2', 'riesgo_medio'): 'Compromiso firmado',
            ('hasta_P2', 'alto_riesgo'): 'Adelanto parcial o contado',
            ('P2_a_P4', 'sin_riesgo'): 'Factura simple',
            ('P2_a_P4', 'riesgo_medio'): 'Letra o compromiso firmado',
            ('P2_a_P4', 'alto_riesgo'): 'Adelanto 50% o garante',
            ('sobre_P4', 'sin_riesgo'): 'Letra/compromiso',
            ('sobre_P4', 'riesgo_medio'): 'Garantia adicional (aval, adelanto)',
            ('sobre_P4', 'alto_riesgo'): 'No otorgar -- ofrecer contado con descuento',
        }
        condicion_txt = MATRIZ_GARANTIA[(tramo_monto, riesgo_txt)]

        ESCALERA = {
            'hasta_P2': 'el agente propone aprobar (checklist + scoring cumplidos)',
            'P2_a_P4': 'requiere aprobacion del dueno, con esta recomendacion como sustento',
            'sobre_P4': 'requiere evaluacion reforzada -- expediente completo antes de decidir',
        }

        ai['result'] = {
            'ok': True,
            'mensaje': (
                'Propuesta de credito para ' + p.name + ': puntaje ' + str(round(puntaje_total, 1)) + '/100 (' + riesgo_txt + '). ' +
                'Monto solicitado ' + str(monto_val) + ' ' + moneda_txt + ' (~' + str(round(monto_usd, 2)) + ' USD, tramo ' + tramo_monto + '). ' +
                'Condicion sugerida: ' + condicion_txt + '. Escalera: ' + ESCALERA[tramo_monto] + '. ' +
                'NOTA: el criterio de referencias/central de riesgo quedo en 0 -- no hay esa integracion todavia; ajustalo a mano si tienes esa informacion.'
            ),
            'datos': {
                'cliente_id': p.id, 'puntaje_total': round(puntaje_total, 1), 'riesgo': riesgo_txt,
                'desglose': {
                    'historial_pago': round(puntos_historial, 1), 'antiguedad': puntos_antiguedad,
                    'verificacion_contacto': puntos_contacto, 'referencias_central_riesgo': puntos_referencias,
                    'volumen_compra': puntos_volumen,
                },
                'monto_solicitado': monto_val, 'moneda': moneda_txt, 'monto_usd_aprox': round(monto_usd, 2),
                'plazo_dias': plazo_val, 'tramo_monto': tramo_monto, 'condicion_sugerida': condicion_txt,
            },
        }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
