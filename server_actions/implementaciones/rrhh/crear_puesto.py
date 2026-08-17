"""Server Action: rrhh / crear_puesto

Primera herramienta de RRHH. Publica el puesto en Reclutamiento
(`hr.job`) con la descripción YA APROBADA por el dueño -- la publicación
es el paso sensible (`aprobacion: "dueno"`), así que el código en sí no
pide confirmación (eso lo hace el agente en la conversación, mismo patrón
que `registrar_decision.py`): solo ejecuta cuando ya lo llaman.

Campos reales verificados con `fields_get` (Reclutamiento está instalado
en este tenant): `name` (obligatorio), `description` (html),
`no_of_recruitment` (integer), `contract_type_id` (m2o a
`hr.contract.type`).

`modalidad` no tiene equivalente directo en el catálogo estándar de Odoo
(`hr.contract.type` trae Permanent/Temporary/Full-Time/Part-Time/etc, no
"planilla"/"honorarios"). Se mapea lo más cercano semánticamente
(planilla->Full-Time, medio_tiempo->Part-Time, practicas->Apprenticeship)
y para "honorarios" (pago por recibo por honorarios, sin relación de
dependencia -- muy común en Perú) NO hay ningún tipo existente que
encaje: se busca/crea "Honorarios (RxH)" la primera vez, mismo criterio
ya usado en `construir_dashboard.py` para el grupo de dashboards que no
tenía equivalente estándar.

`descripcion_aprobada` pierde su `minLength: 100` (Odoo no lo soporta,
ver esquemas_odoo.py) -- se revalida a mano. `vacantes` pierde su
`default: 1` y `minimum: 1` -- también a mano.

**Bug real encontrado y corregido en la prueba en vivo (17-ago-2026):**
la primera versión buscaba el tipo por nombre en inglés a secas
(`('name', '=', 'Full-Time')`). Este tenant corre en `es_ES` (idioma real
del usuario, confirmado con `res.users.lang`) y `hr.contract.type.name`
es un campo TRADUCIDO -- en español ese mismo registro se llama "Tiempo
completo", no "Full-Time" (confirmado leyendo el mismo id con
`context={'lang': 'es_ES'}` vs `'en_US'`). Buscar el string en inglés
bajo el contexto real en español no encontraba nada y el código creaba
un tipo NUEVO y duplicado con el nombre en inglés cada vez. Corregido
usando `env.ref(...)` con el XML ID real de cada tipo estándar de Odoo
(`hr.contract_type_full_time`, etc. -- confirmados con `ir.model.data`,
no adivinados), que es independiente del idioma. Solo "Honorarios (RxH)"
sigue por nombre porque no existe como tipo estándar de Odoo en ningún
idioma -- ahí sí hay que crearlo, y una sola vez por tenant.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
# XML ID real de cada tipo estandar de Odoo (ir.model.data, confirmado en
# vivo) -- independiente del idioma del tenant, a diferencia de buscar por
# "name" (traducido, ver bug documentado arriba).
MODALIDAD_A_XMLID = {
    'planilla': 'hr.contract_type_full_time',
    'medio_tiempo': 'hr.contract_type_part_time',
    'practicas': 'hr.contract_type_apprenticeship',
}
NOMBRE_TIPO_HONORARIOS = 'Honorarios (RxH)'

titulo_txt = (titulo or '').strip()
descripcion_txt = (descripcion_aprobada or '').strip()
modalidad_txt = (modalidad or '').strip()
vacantes_val = vacantes if vacantes else 1
MODALIDADES_VALIDAS = tuple(MODALIDAD_A_XMLID.keys()) + ('honorarios',)

errores = []
if not titulo_txt:
    errores.append('falta el titulo del puesto')
if len(descripcion_txt) < 100:
    # minLength no lo valida Odoo (ver esquemas_odoo.py) -- se valida acá.
    errores.append('descripcion_aprobada debe tener al menos 100 caracteres (llego con ' + str(len(descripcion_txt)) + ')')
if modalidad_txt not in MODALIDADES_VALIDAS:
    errores.append('modalidad debe ser una de: ' + ', '.join(MODALIDADES_VALIDAS))
if vacantes_val < 1:
    errores.append('vacantes debe ser al menos 1')

if errores:
    ai['result'] = {'ok': False, 'mensaje': 'No pude crear el puesto: ' + '; '.join(errores) + '.', 'datos': {}}
else:
    if modalidad_txt == 'honorarios':
        Tipo = env['hr.contract.type']
        tipo_existente = Tipo.search([('name', '=', NOMBRE_TIPO_HONORARIOS)], limit=1)
        tipo = tipo_existente if tipo_existente else Tipo.create({'name': NOMBRE_TIPO_HONORARIOS})
    else:
        tipo = env.ref(MODALIDAD_A_XMLID[modalidad_txt])

    Job = env['hr.job']
    existente = Job.search([('name', '=', titulo_txt)], limit=1)
    valores = {
        'name': titulo_txt,
        'description': descripcion_txt,
        'no_of_recruitment': vacantes_val,
        'contract_type_id': tipo.id,
    }
    if existente:
        existente.write(valores)
        registro = existente
        accion_txt = 'actualizado'
    else:
        registro = Job.create(valores)
        accion_txt = 'creado'

    ai['result'] = {
        'ok': True,
        'mensaje': 'Puesto "' + titulo_txt + '" ' + accion_txt + ' en Reclutamiento (' + modalidad_txt + ', ' + str(vacantes_val) + ' vacante(s)).',
        'datos': {'puesto_id': registro.id, 'modalidad': modalidad_txt, 'vacantes': vacantes_val},
    }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
