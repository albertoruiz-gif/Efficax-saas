"""Server Action: ventas_atencion / agendar_reunion

Octava herramienta con lógica real. Dos modos (`modo`):

- `enlace_citas`: comparte el link de un `appointment.type` (Citas de
  Odoo) para que el cliente elija hora — NO crea ningún `calendar.event`
  directamente, Odoo lo hace cuando el cliente reserva.
- `evento_directo`: crea el `calendar.event` ya con fecha acordada.

El catálogo declara esta regla con `if/then` a nivel raíz del esquema
("si modo=evento_directo, fecha_hora es obligatorio") — Odoo NO soporta
`if`/`then` (ver esquemas_odoo.py: se descarta en silencio, ni siquiera
llega traducido a texto porque es una restricción de nivel raíz, no de
propiedad). Por eso esa regla condicional se valida acá a mano.

Sobre `enlace_citas`: en este tenant NO hay ningún `appointment.type`
configurado todavía (verificado con `search_read`, no asumido) — la rama
de "no hay tipo de cita disponible" no es teórica, es el estado real de
Efficax hoy. Cuando Booster provisione un tenant con Citas configuradas,
el mismo código sirve la URL real sin cambios.

`contacto` y `vendedor` son texto libre (no ids): se buscan por nombre (o
email si `contacto` parece uno) con el mismo patrón "nunca inventar" que
el resto de herramientas — ambiguo o no encontrado se lo decimos al
usuario, no se adivina.

**Corrección de diseño (17-ago-2026):** `fecha_hora` llega en hora LOCAL
de quien habla con el agente. La conversión a UTC ya NO hardcodea el
offset de Perú (+5h) — se lee `env.user.tz_offset` (Odoo lo calcula por
usuario a partir de su zona horaria configurada) para que cualquier
tenant, en cualquier país, agende en su propia hora local sin tocar el
código. Detalle completo del porqué en `rrhh/programar_entrevista.py`
(misma corrección aplicada ahí primero) y en `implementaciones/README.md`.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
modo_val = (modo or '').strip()
vendedor_txt = (vendedor or '').strip()
contacto_txt = (contacto or '').strip()
motivo_txt = (motivo or '').strip()
duracion = duracion_min or 30
fecha_hora_txt = (fecha_hora or '').strip()

errores = []
if modo_val not in ('enlace_citas', 'evento_directo'):
    errores.append('modo debe ser "enlace_citas" o "evento_directo"')
if not vendedor_txt:
    errores.append('falta el vendedor responsable')
if not contacto_txt:
    errores.append('falta el contacto')
if modo_val == 'evento_directo' and not fecha_hora_txt:
    # Regla condicional del catalogo (if/then a nivel raiz): Odoo no la
    # soporta en el esquema (ver esquemas_odoo.py), se valida acá.
    errores.append('evento_directo necesita fecha_hora')

if errores:
    ai['result'] = {'ok': False, 'mensaje': 'No pude agendar: ' + '; '.join(errores) + '.', 'datos': {}}
else:
    Vendedores = env['res.users'].search([
        '|', ('name', 'ilike', vendedor_txt), ('login', 'ilike', vendedor_txt),
    ], limit=5)

    if not Vendedores:
        ai['result'] = {'ok': False, 'mensaje': 'No encontre ningun usuario interno que coincida con "' + vendedor_txt + '".', 'datos': {}}
    elif len(Vendedores) > 1:
        nombres_v = [v.name + ' (id ' + str(v.id) + ')' for v in Vendedores]
        ai['result'] = {'ok': False, 'mensaje': 'Hay varios usuarios que coinciden con "' + vendedor_txt + '". Precisa cual: ' + '; '.join(nombres_v), 'datos': {}}
    elif modo_val == 'enlace_citas':
        Tipos = env['appointment.type'].search([('staff_user_ids', 'in', [Vendedores.id])], limit=1)
        if not Tipos:
            Tipos = env['appointment.type'].search([('active', '=', True)], limit=1)
        if not Tipos:
            ai['result'] = {
                'ok': False,
                'mensaje': 'No hay ningun tipo de cita configurado todavia para compartir el enlace. Hay que crear uno en Citas > Configuracion antes de poder usar esta opcion.',
                'datos': {},
            }
        else:
            enlace = Tipos.website_absolute_url or Tipos.website_url
            ai['result'] = {
                'ok': True,
                'mensaje': 'Enlace de citas para que ' + contacto_txt + ' elija hora: ' + enlace,
                'datos': {'appointment_type_id': Tipos.id, 'enlace': enlace},
            }
    else:
        fecha_dt = False
        for patron in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M'):
            try:
                fecha_dt = datetime.datetime.strptime(fecha_hora_txt, patron)
                break
            except:  # noqa: E722 -- ValueError no esta expuesto en el sandbox de Odoo (NameError real, ver README)
                continue

        if not fecha_dt:
            ai['result'] = {'ok': False, 'mensaje': 'No entendi la fecha_hora "' + fecha_hora_txt + '". Usa el formato AAAA-MM-DD HH:MM.', 'datos': {}}
        else:
            if '@' in contacto_txt:
                Contactos = env['res.partner'].search([('email', '=ilike', contacto_txt)], limit=5)
            else:
                Contactos = env['res.partner'].search([('name', 'ilike', contacto_txt)], limit=5)

            if len(Contactos) > 1:
                nombres_c = [c.name + ' (id ' + str(c.id) + ')' for c in Contactos]
                ai['result'] = {'ok': False, 'mensaje': 'Hay varios contactos que coinciden con "' + contacto_txt + '". Precisa cual: ' + '; '.join(nombres_c), 'datos': {}}
            else:
                # fecha_hora llega en hora LOCAL de quien habla con el
                # agente; calendar.event.start/stop se guardan siempre en
                # UTC a nivel de ORM -- create() no convierte zona horaria
                # por si solo (confirmado en vivo: sin offset, un evento a
                # las 15:00 Lima quedaba guardado y MOSTRADO como 10:00
                # Lima -- 5 horas antes de lo pedido).
                #
                # CORRECCION DE DISENO (17-ago-2026): la primera version
                # hardcodeaba "+timedelta(hours=5)" asumiendo que el tenant
                # siempre iba a estar en Peru -- funcionaba en Efficax
                # porque lo esta, pero rompe para cualquier cliente en otro
                # pais. Corregido leyendo el offset REAL del usuario que
                # ejecuta la herramienta (env.user.tz_offset, un campo
                # 'char' que Odoo ya calcula por usuario a partir de su
                # zona horaria configurada, ej. '-0500') -- asi cualquier
                # tenant agenda en su propia hora local sin tocar codigo.
                # No se usa pytz/zoneinfo (no disponibles en el sandbox,
                # solo env/ai/datetime/UserError lo estan) -- no hace
                # falta, Odoo ya hizo ese calculo por nosotros.
                offset_txt = (env.user.tz_offset or '+0000').strip()
                signo_offset = -1 if offset_txt[:1] == '-' else 1
                horas_offset = int(offset_txt[1:3]) if len(offset_txt) >= 3 else 0
                minutos_offset = int(offset_txt[3:5]) if len(offset_txt) >= 5 else 0
                offset_delta = signo_offset * datetime.timedelta(hours=horas_offset, minutes=minutos_offset)
                fecha_utc = fecha_dt - offset_delta
                valores = {
                    'name': motivo_txt or ('Reunion con ' + contacto_txt),
                    'start': fecha_utc,
                    'stop': fecha_utc + datetime.timedelta(minutes=duracion),
                    'user_id': Vendedores.id,
                    'description': motivo_txt,
                }
                if Contactos:
                    valores['partner_ids'] = [(6, 0, [Contactos.id])]
                evento = env['calendar.event'].create(valores)

                aviso_contacto = '' if Contactos else ' (nota: "' + contacto_txt + '" no es un contacto existente, se registro solo en la descripcion, sin invitacion automatica)'
                ai['result'] = {
                    'ok': True,
                    'mensaje': 'Reunion agendada para el ' + str(fecha_dt) + ' hora local.' + aviso_contacto,
                    'datos': {'evento_id': evento.id, 'vendedor_id': Vendedores.id},
                }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
