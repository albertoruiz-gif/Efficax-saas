"""Server Action: booster / guardar_avance_wizard

Primera herramienta real de Booster (el implementador), no del catálogo de
agentes de cara al cliente — por eso vive en `booster/`, no en
`server_actions/implementaciones/`. Persiste el avance del wizard
conversacional (Fase 1 en esta primera versión) en `x_booster_implementacion`:
un registro por dueño/administrador (identificado por `dueno_email` — NO por
`tenant`, ver más abajo), creado en el primer contacto y actualizado en cada
checkpoint — "la conversación puede cortarse y retomarse días después sin
perder nada" (spec, 01-booster-implementador.md).

**Por qué la llave de continuidad es el email y no el nombre del negocio**
(bug real, encontrado en la primera prueba en vivo): el nombre del negocio
es justo una de las cosas que Fase 1 descubre progresivamente durante la
conversación — al principio no se conoce. Buscar el registro existente por
`x_tenant` partía el wizard en dos: un registro huérfano con un placeholder
("Pendiente - nombre del negocio") del primer mensaje, y otro nuevo una vez
que el nombre real se conocía, sin fusionarse nunca. El email del dueño, en
cambio, se conoce desde el primer mensaje y no cambia durante la
conversación — es la llave correcta.

No usa el saneador `esquemas_odoo.py` porque Booster no es una herramienta
del catálogo `herramientas_esquemas.json` (ese catálogo es para los agentes
de cara al cliente: ventas_atencion, mentor, etc.) — el esquema de este
tool ya se escribió directamente en el formato que Odoo acepta.

`respuestas_json` acumula: no reemplaza el diccionario completo en cada
llamada, hace merge con lo que ya había — así Booster puede ir guardando
una respuesta a la vez sin pisar las anteriores.

**Agregado 21-ago-2026 (pedido de Alberto — "qué falta de la Fase 1"):**
dos parámetros nuevos, cada uno con su propia semántica de guardado:
- `agentes_sugeridos`: se REEMPLAZA entero en cada llamada (como `fase` o
  `tenant`) — Booster manda siempre la lista completa vigente de códigos,
  no un delta. Es la salida más importante de Fase 1 (el carrito
  sugerido que alimenta la Fase 2, todavía sin construir) y antes no
  quedaba registrada en ningún lado.
- `autorizado`: se ACUMULA como `pendiente` — una persona por llamada,
  nunca pisa lo ya guardado. Antes Booster sabía (por el system prompt)
  que podía hablar con quien el dueño autorizara, pero no había dónde
  anotar a quién.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
FASES_VALIDAS = ('descubrimiento', 'propuesta', 'provisioning', 'ajustes', 'residencia')

tenant_txt = (tenant or '').strip()
dueno_nombre_txt = (dueno_nombre or '').strip()
dueno_email_txt = (dueno_email or '').strip()
fase_txt = (fase or '').strip()
respuestas_txt = (respuestas_json or '').strip()
checkpoint_txt = (checkpoint_nota or '').strip()
pendiente_txt = (pendiente or '').strip()
camino_txt = (camino or '').strip().upper()
CAMINOS_VALIDOS = ('A', 'B', 'C')
agentes_sugeridos_txt = (agentes_sugeridos or '').strip()
autorizado_txt = (autorizado or '').strip()
AGENTES_VALIDOS = ('ventas', 'marketing', 'finanzas', 'dashboard', 'legal', 'rrhh', 'inventarios')

errores = []
if not tenant_txt:
    errores.append('falta el tenant/negocio')
if not dueno_nombre_txt or not dueno_email_txt:
    errores.append('falta el nombre o email del dueno/administrador designado')
if fase_txt not in FASES_VALIDAS:
    errores.append('fase invalida')
if camino_txt and camino_txt not in CAMINOS_VALIDOS:
    errores.append('camino debe ser A, B o C')

agentes_lista = []
if agentes_sugeridos_txt:
    agentes_lista = [a.strip().lower() for a in agentes_sugeridos_txt.split(',') if a.strip()]
    agentes_invalidos = [a for a in agentes_lista if a not in AGENTES_VALIDOS]
    if agentes_invalidos:
        errores.append('agentes_sugeridos tiene codigos invalidos: ' + ', '.join(agentes_invalidos) + '. Validos: ' + ', '.join(AGENTES_VALIDOS))

respuestas_nuevas = {}
if respuestas_txt:
    try:
        respuestas_nuevas = json.loads(respuestas_txt)
    except:  # noqa: E722 -- clases de excepcion no expuestas en el sandbox
        respuestas_nuevas = None
    if not isinstance(respuestas_nuevas, dict):
        errores.append('respuestas_json debe ser un objeto JSON valido (clave-valor)')

if errores:
    ai['result'] = {'ok': False, 'mensaje': 'No pude guardar el avance: ' + '; '.join(errores) + '.', 'datos': {}}
else:
    Wizard = env['x_booster_implementacion']
    # La llave de continuidad es el email del dueno, NO el tenant: el nombre
    # del negocio es justo lo que Fase 1 va descubriendo a lo largo de la
    # conversacion, así que buscar por x_tenant partía el wizard en dos
    # registros (uno con el placeholder inicial, otro con el nombre real
    # una vez conocido) -- bug real, detectado en la primera prueba en vivo.
    registro = Wizard.search([('x_dueno_email', '=ilike', dueno_email_txt)], limit=1)
    ahora = datetime.datetime.now()

    if registro:
        respuestas_previas = {}
        if registro.x_respuestas_json:
            try:
                respuestas_previas = json.loads(registro.x_respuestas_json)
            except:  # noqa: E722
                respuestas_previas = {}
        respuestas_previas.update(respuestas_nuevas)
        respuestas_final = respuestas_previas

        checkpoints_prev = registro.x_checkpoints or ''
        pendientes_prev = registro.x_pendientes or ''
        autorizados_prev = registro.x_autorizados or ''
    else:
        respuestas_final = respuestas_nuevas
        checkpoints_prev = ''
        pendientes_prev = ''
        autorizados_prev = ''

    linea_checkpoint = str(ahora) + ' [' + fase_txt + ']'
    if checkpoint_txt:
        linea_checkpoint += ' ' + checkpoint_txt
    checkpoints_final = (checkpoints_prev + '\\n' + linea_checkpoint) if checkpoints_prev else linea_checkpoint

    pendientes_final = pendientes_prev
    if pendiente_txt:
        pendientes_final = (pendientes_prev + '\\n' + pendiente_txt) if pendientes_prev else pendiente_txt

    autorizados_final = autorizados_prev
    if autorizado_txt:
        autorizados_final = (autorizados_prev + '\\n' + autorizado_txt) if autorizados_prev else autorizado_txt

    valores = {
        'x_name': tenant_txt,
        'x_tenant': tenant_txt,
        'x_dueno_nombre': dueno_nombre_txt,
        'x_dueno_email': dueno_email_txt,
        'x_fase_actual': fase_txt,
        'x_respuestas_json': json.dumps(respuestas_final, ensure_ascii=False),
        'x_checkpoints': checkpoints_final,
        'x_pendientes': pendientes_final,
        'x_autorizados': autorizados_final,
        'x_fecha_ultimo_avance': ahora,
    }
    # El camino se descubre UNA vez en Fase 1 y queda: solo se escribe si vino,
    # nunca se pisa con vacio en llamadas posteriores.
    if camino_txt:
        valores['x_camino'] = camino_txt
    # agentes_sugeridos SI se reemplaza entero (a diferencia de camino):
    # Booster manda la lista completa vigente en cada llamada, no un delta.
    if agentes_lista:
        valores['x_agentes_sugeridos'] = ', '.join(agentes_lista)

    if registro:
        registro.write(valores)
        accion_txt = 'actualizado'
    else:
        valores['x_fecha_inicio'] = ahora
        registro = Wizard.create(valores)
        accion_txt = 'creado'

    ai['result'] = {
        'ok': True,
        'mensaje': 'Avance ' + accion_txt + ' para ' + tenant_txt + ' (fase: ' + fase_txt + ').',
        'datos': {'implementacion_id': registro.id, 'fase': fase_txt, 'accion': accion_txt},
    }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
