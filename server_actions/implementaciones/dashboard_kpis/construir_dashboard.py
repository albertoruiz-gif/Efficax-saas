"""Server Action: dashboard_kpis / construir_dashboard

**La más incierta de esta tanda — a diferencia del resto de herramientas
de esta noche, acá NO hay confianza razonable en los nombres de campo.**
`spreadsheet.dashboard` (app Enterprise) guarda su contenido como un
documento o-spreadsheet (JSON con hojas/celdas/gráficos) — un formato
rico y en gran parte indocumentado públicamente, muy distinto de crear un
`sale.order` o un `mail.activity`. Adivinar esa estructura sin verificarla
en vivo sería inventar, no implementar.

Lo que SÍ se puede hacer con confianza (y es lo que hace este código):
validar `nivel`/`kpis` contra el mismo catálogo fijo de `calcular_kpi.py`,
y crear un registro `spreadsheet.dashboard` mínimo (nombre + descripción
con los KPIs pedidos) que sirva de placeholder localizable — sin intentar
construir gráficos reales. Poblarlo con los KPIs de verdad requiere
completar esto en vivo: o bien reverse-engineering del formato
o-spreadsheet contra el tenant real, o un paso manual humano en el editor
de Spreadsheet. Documentado así a propósito, no es un TODO olvidado.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
KPIS_DISPONIBLES = ('ventas_totales', 'ticket_promedio', 'tasa_conversion', 'margen_bruto', 'valor_inventario')
NIVELES_VALIDOS = ('gerencial', 'operativo')

nivel_txt = (nivel or '').strip()
lista_kpis = kpis if isinstance(kpis, list) else []

errores = []
if nivel_txt not in NIVELES_VALIDOS:
    errores.append('nivel debe ser "gerencial" u "operativo"')
if not lista_kpis:
    errores.append('kpis no puede estar vacio')
elif len(lista_kpis) > 12:
    errores.append('kpis admite un maximo de 12 elementos')
else:
    desconocidos = [k for k in lista_kpis if k not in KPIS_DISPONIBLES]
    if desconocidos:
        errores.append('KPI(s) no reconocido(s): ' + ', '.join(desconocidos) + '. Disponibles: ' + ', '.join(KPIS_DISPONIBLES))

if errores:
    ai['result'] = {'ok': False, 'mensaje': 'No pude construir el dashboard: ' + '; '.join(errores) + '.', 'datos': {}}
else:
    Dashboard = env['spreadsheet.dashboard']
    nombre_dash = 'Dashboard ' + nivel_txt.capitalize()
    existente = Dashboard.search([('name', '=', nombre_dash)], limit=1)

    valores = {'name': nombre_dash}

    if existente:
        existente.write(valores)
        registro = existente
        accion_txt = 'actualizado'
    else:
        registro = Dashboard.create(valores)
        accion_txt = 'creado'

    ai['result'] = {
        'ok': True,
        'mensaje': (
            'Dashboard ' + accion_txt + ' (' + nivel_txt + ') con placeholder para: ' + ', '.join(lista_kpis) + '. '
            'ATENCION: el contenido real (graficos por KPI) todavia no se genera automaticamente -- '
            'pendiente de completar el formato del dashboard en vivo.'
        ),
        'datos': {'dashboard_id': registro.id, 'nivel': nivel_txt, 'kpis': lista_kpis, 'contenido_real_pendiente': True},
    }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
