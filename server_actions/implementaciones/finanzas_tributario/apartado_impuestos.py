"""Server Action: finanzas_tributario / apartado_impuestos

Solo lectura (`aprobacion: "ninguna"`). Calcula cuánto reservar para
impuestos según régimen tributario peruano y ventas/compras reales del
mes, mostrando el detalle del cálculo -- y **siempre cierra con
"valídalo con tu contador"**, tal como pide el catálogo. Usa reglas
públicas y conocidas de SUNAT (no un algoritmo propietario de Efficax),
simplificadas a propósito porque el cálculo exacto depende de variables
que este tenant no tiene disponibles (UIT vigente del año, coeficiente
real del ejercicio anterior para el Régimen General, etc.) -- cada
simplificación queda declarada en el resultado, no oculta.

`regimen` dice en el catálogo "se inyecta del expediente" -- ese
expediente (Fase 4 de Booster) no existe todavía en este tenant, así
que se recibe como parámetro explícito en cada llamada, no se asume.

Reglas aplicadas (simplificadas, PÚBLICAS, con la salvedad explícita en
cada caso):
- **NRUS**: cuota fija según categoría de ingresos/compras mensuales
  (categoria 1: hasta S/5,000 -> S/20; categoria 2: hasta S/8,000 ->
  S/50; sobre S/8,000 -> ya no calificaria para NRUS, se avisa). Sin IGV
  separado.
- **RER**: 1.5% de las ventas netas del mes (renta) + IGV 18% (ventas -
  compras) igual que el resto de regimenes con IGV.
- **MYPE Tributario**: 1% de los ingresos netos del mes como pago a
  cuenta (simplificado: asume que sigue dentro del tramo de hasta 15
  UIT anuales -- si supera eso el % sube a 1.5%, y este calculo NO lo
  verifica) + IGV 18%.
- **GENERAL**: 1.5% de los ingresos netos del mes como pago a cuenta
  (aproximación estándar -- el coeficiente real depende de la
  declaración anual del ejercicio anterior, que no está disponible acá)
  + IGV 18%.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
REGIMENES_VALIDOS = ('NRUS', 'RER', 'MYPE', 'GENERAL')
TASA_IGV = 0.18

mes_txt = (mes or '').strip()
regimen_txt = (regimen or '').strip().upper()

anio = False
mes_num = False
if len(mes_txt) == 7 and mes_txt[4] == '-':
    try:
        anio = int(mes_txt[0:4])
        mes_num = int(mes_txt[5:7])
    except:  # noqa: E722 -- clases de excepcion no expuestas en el sandbox
        anio = False
        mes_num = False

errores = []
if not anio or not mes_num or mes_num < 1 or mes_num > 12:
    errores.append('mes debe tener formato AAAA-MM valido')
if regimen_txt not in REGIMENES_VALIDOS:
    errores.append('regimen debe ser una de: ' + ', '.join(REGIMENES_VALIDOS))

if errores:
    ai['result'] = {'ok': False, 'mensaje': 'No pude calcular el apartado: ' + '; '.join(errores) + '.', 'datos': {}}
else:
    desde_dt = datetime.date(anio, mes_num, 1)
    if mes_num == 12:
        hasta_dt = datetime.date(anio, 12, 31)
    else:
        hasta_dt = datetime.date(anio, mes_num + 1, 1) - datetime.timedelta(days=1)

    Move = env['account.move']
    ventas = Move.search([
        ('move_type', 'in', ('out_invoice', 'out_refund')), ('state', '=', 'posted'),
        ('invoice_date', '>=', str(desde_dt)), ('invoice_date', '<=', str(hasta_dt)),
    ])
    compras = Move.search([
        ('move_type', 'in', ('in_invoice', 'in_refund')), ('state', '=', 'posted'),
        ('invoice_date', '>=', str(desde_dt)), ('invoice_date', '<=', str(hasta_dt)),
    ])
    ventas_netas = sum(ventas.mapped('amount_untaxed'))
    compras_netas = sum(compras.mapped('amount_untaxed'))

    avisos = []
    if regimen_txt == 'NRUS':
        base_nrus = max(ventas_netas, compras_netas)
        if base_nrus <= 5000:
            cuota_renta = 20.0
        elif base_nrus <= 8000:
            cuota_renta = 50.0
        else:
            cuota_renta = 50.0
            avisos.append('ventas/compras superan S/8,000 -- este negocio ya no calificaria para NRUS, valida el cambio de regimen con tu contador')
        igv_por_pagar = 0.0
        avisos.append('NRUS no declara IGV por separado, va incluido en la cuota fija')
    else:
        igv_ventas = ventas_netas * TASA_IGV
        igv_compras = compras_netas * TASA_IGV
        igv_por_pagar = max(0.0, igv_ventas - igv_compras)

        if regimen_txt == 'RER':
            cuota_renta = ventas_netas * 0.015
        elif regimen_txt == 'MYPE':
            cuota_renta = ventas_netas * 0.01
            avisos.append('asume que los ingresos netos del ejercicio siguen dentro del tramo de 15 UIT anuales -- si ya lo supero, la tasa sube a 1.5%, esta herramienta no lo verifica')
        else:  # GENERAL
            cuota_renta = ventas_netas * 0.015
            avisos.append('usa 1.5% como aproximacion estandar -- el coeficiente real depende de la declaracion anual del ejercicio anterior, no disponible en este calculo')

    total_apartar = cuota_renta + igv_por_pagar

    ai['result'] = {
        'ok': True,
        'mensaje': (
            'Apartado sugerido para ' + mes_txt + ' (' + regimen_txt + '): renta S/' + str(round(cuota_renta, 2)) +
            ' + IGV S/' + str(round(igv_por_pagar, 2)) + ' = S/' + str(round(total_apartar, 2)) + '. ' +
            'Calculo: ventas netas S/' + str(round(ventas_netas, 2)) + ', compras netas S/' + str(round(compras_netas, 2)) + '. ' +
            ('Avisos: ' + '; '.join(avisos) + '. ' if avisos else '') +
            'VALIDALO CON TU CONTADOR antes de apartar o pagar -- este calculo es una aproximacion, no una declaracion oficial.'
        ),
        'datos': {
            'mes': mes_txt, 'regimen': regimen_txt, 'ventas_netas': round(ventas_netas, 2), 'compras_netas': round(compras_netas, 2),
            'renta_estimada': round(cuota_renta, 2), 'igv_estimado': round(igv_por_pagar, 2), 'total_apartar': round(total_apartar, 2),
            'avisos': avisos,
        },
    }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
