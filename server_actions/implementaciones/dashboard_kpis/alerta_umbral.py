"""Server Action: dashboard_kpis / alerta_umbral

Configura una alerta automática para cuando un KPI cruza el umbral pactado.

**Reescrita de raiz el 17-ago-2026 tras verificar en vivo que el enfoque
original (`base.automation`) estaba mal elegido, no solo mal tipeado.**
`base.automation` con `trigger='on_time'` ("Based on date field") evalua
un campo Fecha/Datetime PROPIO DE CADA REGISTRO del modelo (ej. una
actividad vence en X dias despues de su `date_deadline`) -- no sirve para
"revisa este KPI de negocio cada N dias", que no depende de ningun campo
fecha de un registro puntual. El mecanismo correcto de Odoo para eso es
`ir.cron` (Acciones Planificadas): un job periodico que ejecuta `code`
sin iterar registros. Confirmado con `fields_get`: `ir.cron` tambien
hereda de `ir.actions.server` (mismo patron `state='code'`), asi que la
guarda y el resto del codigo de esta herramienta no cambian de forma.

De paso, el codigo generado para la automatizacion ya NO es un
placeholder -- reusa la formula real de `calcular_kpi.py` (incluyendo el
fix de `margen_bruto`: `sale.report` no tiene `margin` ni `order_id` en
este tenant, se calcula a mano desde `sale.order.line`) y notifica
creando un `mail.activity` real cuando el umbral se cruza -- no manda
email/whatsapp por su cuenta, deja una tarea visible que el humano decide
como atender.

Probado en vivo disparando el cron manualmente con
`ir.cron.method_direct_trigger()` (existe justo para esto, no hay que
esperar al `nextcall` real) -- ver README para el detalle de la prueba.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
KPIS_DISPONIBLES = ('ventas_totales', 'ticket_promedio', 'tasa_conversion', 'margen_bruto', 'valor_inventario')
DIRECCIONES_VALIDAS = ('por_debajo', 'por_encima')

kpi_txt = (kpi or '').strip()
umbral_val = umbral
direccion_txt = (direccion or '').strip()
notificar_txt = (notificar_a or '').strip()

errores = []
if kpi_txt not in KPIS_DISPONIBLES:
    errores.append('no reconozco el KPI "' + kpi_txt + '". Disponibles: ' + ', '.join(KPIS_DISPONIBLES))
if umbral_val is None:
    errores.append('falta el umbral')
if direccion_txt not in DIRECCIONES_VALIDAS:
    errores.append('direccion debe ser "por_debajo" o "por_encima"')
if not notificar_txt:
    errores.append('falta a quien notificar')

if errores:
    ai['result'] = {'ok': False, 'mensaje': 'No pude configurar la alerta: ' + '; '.join(errores) + '.', 'datos': {}}
else:
    Usuarios = env['res.users'].search([
        '|', ('name', 'ilike', notificar_txt), ('login', 'ilike', notificar_txt),
    ], limit=5)

    if not Usuarios:
        ai['result'] = {'ok': False, 'mensaje': 'No encontre ningun usuario que coincida con "' + notificar_txt + '".', 'datos': {}}
    elif len(Usuarios) > 1:
        nombres = [u.name + ' (id ' + str(u.id) + ')' for u in Usuarios]
        ai['result'] = {'ok': False, 'mensaje': 'Hay varios usuarios que coinciden con "' + notificar_txt + '". Precisa cual: ' + '; '.join(nombres), 'datos': {}}
    else:
        nombre_alerta = 'Alerta KPI: ' + kpi_txt + ' ' + direccion_txt + ' ' + str(umbral_val)

        # Codigo que ejecuta el cron cada vez que corre -- MISMA formula real
        # de calcular_kpi.py (con el fix de margen_bruto), duplicada porque
        # cada Server Action / ir.cron es un blob independiente en el sandbox.
        codigo_cron = (
            "Sale = env['sale.order']\\n"
            "hoy = datetime.date.today()\\n"
            "desde_dt = hoy - datetime.timedelta(days=30)\\n"
            "ordenes = Sale.search([('date_order', '>=', str(desde_dt)), ('date_order', '<=', str(hoy)), ('state', 'in', ['sale', 'done'])])\\n"
            "kpi_objetivo = '" + kpi_txt + "'\\n"
            "if kpi_objetivo == 'ventas_totales':\\n"
            "    valor_kpi = sum(ordenes.mapped('amount_total'))\\n"
            "elif kpi_objetivo == 'ticket_promedio':\\n"
            "    total_ = sum(ordenes.mapped('amount_total'))\\n"
            "    n_ = len(ordenes)\\n"
            "    valor_kpi = (total_ / n_) if n_ else 0.0\\n"
            "elif kpi_objetivo == 'tasa_conversion':\\n"
            "    Lead = env['crm.lead']\\n"
            "    leads_ = Lead.search([('create_date', '>=', str(desde_dt) + ' 00:00:00'), ('create_date', '<=', str(hoy) + ' 23:59:59')])\\n"
            "    total_leads_ = len(leads_)\\n"
            "    ganados_ = len(leads_.filtered(lambda l_: l_.stage_id.is_won))\\n"
            "    valor_kpi = (ganados_ / total_leads_ * 100) if total_leads_ else 0.0\\n"
            "elif kpi_objetivo == 'margen_bruto':\\n"
            "    Linea = env['sale.order.line']\\n"
            "    lineas_ = Linea.search([('order_id', 'in', ordenes.ids)])\\n"
            "    ventas_ = sum(lineas_.mapped('price_subtotal'))\\n"
            "    costo_ = sum(l_.product_uom_qty * l_.product_id.standard_price for l_ in lineas_)\\n"
            "    valor_kpi = ((ventas_ - costo_) / ventas_ * 100) if ventas_ else 0.0\\n"
            "else:\\n"
            "    Quant = env['stock.quant']\\n"
            "    quants_ = Quant.search([('location_id.usage', '=', 'internal')])\\n"
            "    valor_kpi = sum(q_.quantity * q_.product_id.standard_price for q_ in quants_)\\n"
            "umbral_ = " + repr(umbral_val) + "\\n"
            "cruzado = (valor_kpi < umbral_) if '" + direccion_txt + "' == 'por_debajo' else (valor_kpi > umbral_)\\n"
            "if cruzado:\\n"
            "    modelo_ = env['ir.model']._get('res.company')\\n"
            "    env['mail.activity'].create({\\n"
            "        'res_model_id': modelo_.id,\\n"
            "        'res_id': env.company.id,\\n"
            "        'activity_type_id': env.ref('mail.mail_activity_data_todo').id,\\n"
            "        'user_id': " + str(Usuarios.id) + ",\\n"
            "        'summary': 'Alerta KPI: " + kpi_txt + " " + direccion_txt + " de " + str(umbral_val) + "',\\n"
            "        'note': kpi_objetivo + ' = ' + str(valor_kpi) + ' (umbral " + direccion_txt + " " + str(umbral_val) + ")',\\n"
            "    })\\n"
        )

        modelo_res_company = env['ir.model'].search([('model', '=', 'res.company')], limit=1)

        Cron = env['ir.cron']
        existente = Cron.search([('name', '=', nombre_alerta)], limit=1)
        valores = {
            'name': nombre_alerta,
            'model_id': modelo_res_company.id,
            'state': 'code',
            'code': codigo_cron,
            'interval_number': 1,
            'interval_type': 'days',
            'nextcall': (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
            'user_id': env.user.id,
            'active': True,
        }
        if existente:
            existente.write(valores)
            registro = existente
            accion_txt = 'actualizada'
        else:
            registro = Cron.create(valores)
            accion_txt = 'creada'

        ai['result'] = {
            'ok': True,
            'mensaje': (
                'Alerta ' + accion_txt + ': ' + kpi_txt + ' ' + direccion_txt + ' de ' + str(umbral_val) +
                ', se revisa una vez al dia (ultimos 30 dias moviles) y notifica a ' + Usuarios.name +
                ' con una tarea si se cruza el umbral.'
            ),
            'datos': {'cron_id': registro.id, 'kpi': kpi_txt, 'umbral': umbral_val, 'notificar_a_id': Usuarios.id},
        }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
