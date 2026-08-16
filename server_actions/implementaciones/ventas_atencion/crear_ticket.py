"""Server Action: ventas_atencion / crear_ticket

Cuarta herramienta con lógica real. Crea un `helpdesk.ticket` para soporte
o reclamo.

Decisiones tomadas al implementar (documentadas porque no eran obvias del
esquema):

- `team_id` NO se fija a mano: no hay forma confiable de saber, desde el
  catálogo, a qué equipo de Helpdesk debe caer un tenant dado (este mismo
  tenant tiene DOS equipos llamados "Atención al cliente" con ids
  distintos — verificado con `search_read`, no asumido). Se deja que Odoo
  aplique su propio default; fijarlo a mano habría sido hardcodear un id
  que no es portable entre tenants.
- No existe un campo dedicado para "Libro de Reclamaciones" en este tenant
  (verificado con `fields_get`: sin `x_libro_reclamaciones` ni similar, y
  `helpdesk.tag` está vacío). Se marca de la única forma disponible sin
  inventar infraestructura nueva: prefijo visible en el asunto, prioridad
  forzada a urgente, y un `mail.activity` (tipo "To-Do", buscado por
  nombre — no por id, para no depender de un id fijo) con el plazo legal
  peruano de 30 días calendario para responder un reclamo formal. Ese
  plazo de 30 días es un supuesto de negocio (Código de Protección al
  Consumidor, Perú) — si Efficax confirma otro plazo, se ajusta acá.
- `numero_pedido` es opcional y no se linkea como relación (no se asume
  que el módulo `helpdesk_sale` esté instalado en todos los tenants,
  distinto por instalación): se vuelca como texto en la descripción.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
PLAZO_LIBRO_RECLAMACIONES_DIAS = 30  # Codigo de Proteccion al Consumidor (Peru); confirmar con Efficax

tipo_ticket = (tipo or '').strip()
asunto_txt = (asunto or '').strip()
descripcion_txt = (descripcion or '').strip()
severidad_txt = (severidad or '').strip()
pedido_ref = (numero_pedido or '').strip()
es_libro = bool(es_libro_reclamaciones)
expectativa = (que_espera_cliente or '').strip()

errores = []
if tipo_ticket not in ('soporte', 'reclamo'):
    errores.append('tipo debe ser "soporte" o "reclamo"')
if not asunto_txt:
    errores.append('falta el asunto')
if not descripcion_txt:
    errores.append('falta la descripcion')
if severidad_txt not in ('baja', 'media', 'alta'):
    errores.append('severidad debe ser "baja", "media" o "alta"')

if errores:
    ai['result'] = {'ok': False, 'mensaje': 'No pude crear el ticket: ' + '; '.join(errores) + '.', 'datos': {}}
else:
    MAPA_PRIORIDAD = {'baja': '0', 'media': '1', 'alta': '2'}
    prioridad = MAPA_PRIORIDAD[severidad_txt]

    cuerpo_desc = descripcion_txt
    if pedido_ref:
        cuerpo_desc += '\\n\\nPedido relacionado: ' + pedido_ref
    if expectativa:
        cuerpo_desc += '\\n\\nQue espera el cliente: ' + expectativa

    nombre_ticket = asunto_txt
    if es_libro:
        nombre_ticket = '[LIBRO DE RECLAMACIONES] ' + nombre_ticket
        prioridad = '3'  # urgente: hay un plazo legal corriendo

    Ticket = env['helpdesk.ticket']
    ticket = Ticket.create({
        'name': nombre_ticket,
        'description': cuerpo_desc,
        'priority': prioridad,
    })

    if es_libro:
        # activity_schedule() (del mixin mail.activity.mixin que hereda
        # helpdesk.ticket) en vez de buscar ir.model / mail.activity.type a
        # mano y crear mail.activity directo: primero intento (buscar
        # ir.model + mail.activity.type por nombre) fallaba en SILENCIO en
        # el chat real -- el ticket se creaba bien pero la actividad nunca
        # aparecia, sin ningun error visible (probablemente el usuario real
        # que ejecuta la herramienta no tiene acceso de lectura a ir.model,
        # que es tecnico/oculto por defecto). activity_schedule resuelve el
        # tipo por XML ID via env.ref, que si es de uso general.
        vencimiento = (datetime.datetime.now() + datetime.timedelta(days=PLAZO_LIBRO_RECLAMACIONES_DIAS)).date()
        ticket.activity_schedule(
            'mail.mail_activity_data_todo',
            date_deadline=vencimiento,
            summary='Responder reclamo del Libro de Reclamaciones (plazo legal)',
            note='Ticket #' + str(ticket.id) + ': ' + nombre_ticket + '. Responder antes del plazo legal.',
            user_id=env.user.id,
        )

    ai['result'] = {
        'ok': True,
        'mensaje': 'Ticket creado' + (' y marcado para el Libro de Reclamaciones (recordatorio de plazo legal agendado).' if es_libro else '.'),
        'datos': {'ticket_id': ticket.id, 'tipo': tipo_ticket, 'severidad': severidad_txt, 'es_libro_reclamaciones': es_libro},
    }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
