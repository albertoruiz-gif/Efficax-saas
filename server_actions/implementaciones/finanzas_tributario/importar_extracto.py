"""Server Action: finanzas_tributario / importar_extracto

`aprobacion: "confirmar"`. Importa un extracto bancario y crea el
`account.bank.statement` + `account.bank.statement.line` en Odoo.

**Limitación real y honesta del sandbox de IA:** no hay `open()`,
`__import__` ni ninguna librería de parseo (`openpyxl`, `xlrd`, ni
siquiera el módulo estándar `csv`) disponible -- confirmado en
`guarda_llave.py`, solo `env`/`ai`/`datetime`/`UserError` existen. Un
`.xlsx` real (formato binario zip) **no se puede parsear** en este
entorno. Lo que SÍ se puede hacer sin librerías: leer `ir.attachment.raw`
como texto y partirlo a mano por líneas/comas si el archivo es texto
plano (CSV) -- por eso esta herramienta solo soporta CSV, no Excel
binario, y lo dice explícito si el archivo no se puede decodificar como
texto.

**El mapeo de columnas por banco (BCP/BBVA/Interbank/Scotiabank) que el
catálogo dice que "Booster instaló en el provisioning" NO EXISTE
todavía** -- Fase 3 nunca corrió en este tenant. El mapeo de abajo
(fecha, descripción, monto en ese orden) es un **placeholder razonable,
no verificado contra un archivo real de ningún banco peruano** -- se
declara así en cada respuesta. Reemplazar en cuanto llegue un extracto
real de prueba.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
BANCOS_CONOCIDOS = ('bcp', 'bbva', 'interbank', 'scotiabank')

banco_txt = (banco or '').strip().lower()

Attachment = env['ir.attachment']
adjunto = Attachment.browse(adjunto_id) if adjunto_id else Attachment.browse()

Diario = env['account.journal']
diario = Diario.browse(diario_id) if diario_id else Diario.browse()

errores = []
if not adjunto.exists():
    errores.append('no encontre ningun archivo con adjunto_id ' + str(adjunto_id))
if banco_txt not in BANCOS_CONOCIDOS:
    errores.append('banco debe ser uno de: ' + ', '.join(BANCOS_CONOCIDOS))
if not diario.exists():
    errores.append('no encontre ningun diario con diario_id ' + str(diario_id))
elif diario.type != 'bank':
    errores.append('el diario "' + diario.name + '" no es un diario bancario')

if errores:
    ai['result'] = {'ok': False, 'mensaje': 'No pude importar el extracto: ' + '; '.join(errores) + '.', 'datos': {}}
else:
    contenido_txt = False
    try:
        contenido_txt = adjunto.raw.decode('utf-8')
    except:  # noqa: E722 -- clases de excepcion no expuestas en el sandbox
        try:
            contenido_txt = adjunto.raw.decode('latin-1')
        except:  # noqa: E722
            contenido_txt = False

    if not contenido_txt:
        ai['result'] = {
            'ok': False,
            'mensaje': 'No pude leer el archivo como texto -- si es un .xlsx real (binario), esta herramienta no puede parsearlo todavia (no hay libreria de Excel en este entorno). Exporta el extracto como CSV desde la banca web y vuelve a intentar.',
            'datos': {},
        }
    else:
        primera_linea = contenido_txt.split('\\n')[0] if contenido_txt else ''
        separador = ';' if primera_linea.count(';') >= primera_linea.count(',') else ','

        filas_txt = [f for f in contenido_txt.split('\\n') if f.strip()]
        filas_datos = filas_txt[1:] if len(filas_txt) > 1 else []  # asume 1a fila = encabezado

        MAPEO_PLACEHOLDER = {'fecha': 0, 'descripcion': 1, 'monto': 2}  # NO verificado contra un extracto real -- ver docstring

        lineas_creadas = []
        filas_con_error = []
        for i, fila in enumerate(filas_datos):
            columnas = fila.split(separador)
            if len(columnas) <= max(MAPEO_PLACEHOLDER.values()):
                filas_con_error.append({'fila': i + 2, 'motivo': 'columnas insuficientes'})
                continue
            fecha_txt = columnas[MAPEO_PLACEHOLDER['fecha']].strip()
            descripcion_txt = columnas[MAPEO_PLACEHOLDER['descripcion']].strip()
            monto_txt = columnas[MAPEO_PLACEHOLDER['monto']].strip().replace(',', '')

            fecha_ok = False
            for patron in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
                try:
                    fecha_ok = datetime.datetime.strptime(fecha_txt, patron).date()
                    break
                except:  # noqa: E722
                    continue

            monto_ok = False
            try:
                monto_ok = float(monto_txt)
            except:  # noqa: E722
                monto_ok = False

            if not fecha_ok or monto_ok is False:
                filas_con_error.append({'fila': i + 2, 'motivo': 'fecha o monto no reconocidos', 'contenido': fila})
                continue

            lineas_creadas.append({'date': str(fecha_ok), 'payment_ref': descripcion_txt or 'Movimiento importado', 'amount': monto_ok, 'journal_id': diario.id})

        if not lineas_creadas:
            ai['result'] = {
                'ok': False,
                'mensaje': 'No pude reconocer ninguna fila valida en el archivo con el mapeo de columnas placeholder (fecha, descripcion, monto). Revisa el formato o dime el orden real de columnas.',
                'datos': {'filas_con_error': filas_con_error},
            }
        else:
            statement = env['account.bank.statement'].create({
                'name': 'Extracto ' + banco_txt.upper() + ' -- ' + str(datetime.date.today()),
                'journal_id': diario.id,
                'line_ids': [(0, 0, li) for li in lineas_creadas],
            })

            ai['result'] = {
                'ok': True,
                'mensaje': (
                    str(len(lineas_creadas)) + ' movimiento(s) importado(s) al extracto "' + statement.name + '" (diario ' + diario.name + '). ' +
                    (str(len(filas_con_error)) + ' fila(s) con error, ver datos. ' if filas_con_error else '') +
                    'ATENCION: el mapeo de columnas para ' + banco_txt.upper() + ' es un placeholder no verificado contra un extracto real -- revisa que fecha/descripcion/monto quedaron en la columna correcta.'
                ),
                'datos': {'statement_id': statement.id, 'lineas_importadas': len(lineas_creadas), 'filas_con_error': filas_con_error, 'mapeo_usado': MAPEO_PLACEHOLDER},
            }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
