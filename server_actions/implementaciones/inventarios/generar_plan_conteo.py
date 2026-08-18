"""Server Action: inventarios / generar_plan_conteo

`aprobacion: "ninguna"`. Arma el calendario de conteo cíclico del
período por clase ABC, con las frecuencias que el catálogo pide
explícito: A = semanal (7 días), B = quincenal (14 días), C = mensual
(30 días) -- convención estándar de conteo cíclico, no inventada.

Solo puede programar productos que YA tienen `x_clase_abc` fijado
(corre `clasificar_abc` primero si no) -- este campo es custom, creado
por `instalar_campos_inventarios.py`, no existe de forma nativa.

**Limitación real:** `x_proximo_conteo_ciclico` es una fecha ÚNICA por
producto (no una lista de fechas futuras) -- así que este plan solo fija
la PRIMERA fecha de conteo de cada producto dentro del período. Cuando
`entregar_conteo_dia` entregue y se registre ese conteo, hay que volver
a correr este generador para programar la siguiente vuelta -- no es un
calendario recurrente automático todavía.

Las fechas dentro de cada clase se reparten en varios días (no todas el
mismo día) usando el id del producto como desempate, para no saturar un
solo día de conteo.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
FRECUENCIA_DIAS = {'A': 7, 'B': 14, 'C': 30}

desde_txt = (periodo_desde or '').strip()
hasta_txt = (periodo_hasta or '').strip()

try:
    desde_dt = datetime.datetime.strptime(desde_txt, '%Y-%m-%d').date() if desde_txt else False
except:  # noqa: E722 -- clases de excepcion no expuestas en el sandbox
    desde_dt = False
try:
    hasta_dt = datetime.datetime.strptime(hasta_txt, '%Y-%m-%d').date() if hasta_txt else False
except:  # noqa: E722
    hasta_dt = False

if not desde_dt or not hasta_dt:
    ai['result'] = {'ok': False, 'mensaje': 'periodo.desde y periodo.hasta deben ser fechas validas en formato AAAA-MM-DD.', 'datos': {}}
elif desde_dt > hasta_dt:
    ai['result'] = {'ok': False, 'mensaje': 'periodo.desde no puede ser posterior a periodo.hasta.', 'datos': {}}
else:
    dias_periodo = (hasta_dt - desde_dt).days + 1
    Producto = env['product.template']
    programados = []
    sin_clase_count = Producto.search_count([('x_clase_abc', '=', False), ('active', '=', True)])

    for clase, frecuencia in FRECUENCIA_DIAS.items():
        productos = Producto.search([('x_clase_abc', '=', clase), ('active', '=', True)])
        for producto in productos:
            offset_reparto = producto.id % frecuencia
            fecha_programada = desde_dt + datetime.timedelta(days=offset_reparto)
            if fecha_programada > hasta_dt:
                fecha_programada = desde_dt
            producto.write({'x_proximo_conteo_ciclico': str(fecha_programada)})
            programados.append({'producto_id': producto.id, 'sku': producto.default_code or False, 'clase': clase, 'fecha_programada': str(fecha_programada)})

    ai['result'] = {
        'ok': True,
        'mensaje': (
            str(len(programados)) + ' producto(s) programado(s) para conteo entre ' + str(desde_dt) + ' y ' + str(hasta_dt) + ' (' + str(dias_periodo) + ' dias). ' +
            (str(sin_clase_count) + ' producto(s) sin clase ABC quedaron fuera del plan -- corre clasificar_abc primero. ' if sin_clase_count else '')
        ),
        'datos': {'programados': programados, 'sin_clase_abc': sin_clase_count},
    }
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
