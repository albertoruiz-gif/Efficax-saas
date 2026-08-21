"""Server Action: booster / evaluar_implementacion

Evalúa los vacíos de una implementación Odoo contra la Norma de
Implementación de Booster (`booster/fuentes/NORMA-IMPLEMENTACION.md`) -- la
operacionalización del manual "Implementación del Sistema Odoo --
Localización Perú" que Alberto aportó el 19-ago-2026 con la instrucción
de complementarlo y adoptarlo como norma.

Corre SOLO los checks marcados `✓auto` en la norma: los que se pueden
verificar leyendo el Odoo real sin preguntarle nada al dueño. Los ítems
que requieren conversación (migración de datos, valoración de inventario
elegida, flujos de aprobación) se listan aparte como "a conversar", no
se adivinan.

Doble uso (pedido de Alberto):
- Cliente nuevo: se corre al cerrar cada fase para confirmar que la fase
  quedó completa antes de pasar a la siguiente.
- Odoo ya andando (Fase 1-bis, "ya tiene Odoo"): se corre al inicio para
  saber qué tan lejos está de la norma y por dónde empezar.

Cada check devuelve: id de la norma, estado (ok / falta / parcial),
detalle concreto (qué registros fallan, no solo "hay un problema"), y
prioridad (bloqueante / importante / recomendado). La salida está
pensada para que Booster la convierta en un plan de acción hablado, no
para leerse cruda.

Todos los modelos y campos consultados se verificaron en vivo en el
tenant de Efficax el 19-ago-2026 (fields_get + lectura real) -- ninguno
está asumido.
"""

from guarda_llave import GUARDA_TEMPLATE

CUERPO = '''
alcance_txt = (alcance or 'completo').strip().lower()
FASES_VALIDAS = ('completo', 'fundaciones', 'datos_maestros', 'operativo')
if alcance_txt not in FASES_VALIDAS:
    alcance_txt = 'completo'

hallazgos = []

def registrar(id_norma, estado, prioridad, titulo, detalle):
    hallazgos.append({
        'id': id_norma, 'estado': estado, 'prioridad': prioridad,
        'titulo': titulo, 'detalle': detalle,
    })

# ---------- FASE 0: FUNDACIONES ----------
if alcance_txt in ('completo', 'fundaciones'):
    compania = env.company

    # 0.2 pais y moneda
    pais_ok = compania.country_id and compania.country_id.code == 'PE'
    moneda_ok = compania.currency_id and compania.currency_id.name == 'PEN'
    if pais_ok and moneda_ok:
        registrar('0.2', 'ok', 'bloqueante', 'Pais Peru y moneda PEN', 'Configurados correctamente.')
    else:
        registrar('0.2', 'falta', 'bloqueante', 'Pais Peru y moneda PEN',
            'Pais: ' + (compania.country_id.name if compania.country_id else 'sin definir') +
            ' / Moneda: ' + (compania.currency_id.name if compania.currency_id else 'sin definir') +
            '. Deben ser Peru y PEN.')

    # 0.3 modulos de localizacion
    mods_req = ['l10n_pe', 'l10n_pe_edi', 'l10n_pe_reports', 'l10n_pe_edi_stock']
    instalados = env['ir.module.module'].search([('name', 'in', mods_req), ('state', '=', 'installed')]).mapped('name')
    faltan = [m for m in mods_req if m not in instalados]
    if not faltan:
        registrar('0.3', 'ok', 'bloqueante', 'Modulos de localizacion Peru', 'Los 4 modulos instalados.')
    else:
        registrar('0.3', 'falta', 'bloqueante', 'Modulos de localizacion Peru',
            'Faltan instalar: ' + ', '.join(faltan) + '.')

    # 0.4 datos que trae la localizacion
    n_imp = env['account.tax'].search_count([('type_tax_use', '=', 'sale'), ('l10n_pe_edi_tax_code', '!=', False)])
    n_tipos_doc = env['l10n_latam.document.type'].search_count([('country_id.code', '=', 'PE')]) if 'l10n_latam.document.type' in env else 0
    n_tipos_id = env['l10n_latam.identification.type'].search_count([]) if 'l10n_latam.identification.type' in env else 0
    if n_imp >= 3 and n_tipos_doc >= 3 and n_tipos_id >= 2:
        registrar('0.4', 'ok', 'bloqueante', 'Datos base de la localizacion',
            str(n_imp) + ' impuestos con codigo SUNAT, ' + str(n_tipos_doc) + ' tipos de documento, ' + str(n_tipos_id) + ' tipos de identificacion.')
    else:
        registrar('0.4', 'parcial', 'bloqueante', 'Datos base de la localizacion',
            'Impuestos con codigo SUNAT: ' + str(n_imp) + ', tipos de documento PE: ' + str(n_tipos_doc) + ', tipos de identificacion: ' + str(n_tipos_id) + '. Revisar que la localizacion haya cargado todo.')

    # 0.5 datos de compania
    faltan_c = []
    if not compania.vat: faltan_c.append('RUC')
    if not compania.street: faltan_c.append('direccion')
    if not compania.city: faltan_c.append('distrito/ciudad')
    if not compania.state_id: faltan_c.append('departamento')
    if not faltan_c:
        registrar('0.5', 'ok', 'bloqueante', 'Datos de la compania', 'RUC ' + compania.vat + ', direccion completa.')
    else:
        registrar('0.5', 'falta', 'bloqueante', 'Datos de la compania', 'Faltan: ' + ', '.join(faltan_c) + '. SUNAT rechaza comprobantes sin estos datos.')

    # 0.6 proveedor de firma (OSE). Sin getattr: el sandbox no lo expone
    # (NameError en vivo, 19-ago-2026). El campo existe si l10n_pe_edi esta
    # instalado -- se lee via _fields para no reventar si no lo esta.
    prov = compania.l10n_pe_edi_provider if 'l10n_pe_edi_provider' in compania._fields else False
    if prov:
        registrar('0.6', 'ok', 'bloqueante', 'Proveedor de firma digital (OSE)', 'Proveedor: ' + str(prov) + '.')
    else:
        registrar('0.6', 'falta', 'bloqueante', 'Proveedor de firma digital (OSE)', 'No hay proveedor elegido (IAP, Digiflow o SUNAT). Sin esto no se puede facturar electronicamente.')

    # 0.7 usuarios
    n_users = env['res.users'].search_count([('share', '=', False)])
    if n_users >= 2:
        registrar('0.7', 'ok', 'importante', 'Usuarios internos', str(n_users) + ' usuarios internos. Verificar a mano que no todos sean administradores.')
    else:
        registrar('0.7', 'parcial', 'importante', 'Usuarios internos', 'Solo ' + str(n_users) + ' usuario. Para operar se necesitan al menos los roles Vendedor/Contador separados del Administrador.')

    # 0.9 diarios con documentos SUNAT
    diarios_venta = env['account.journal'].search([('type', '=', 'sale')])
    con_docs = diarios_venta.filtered(lambda j: j.l10n_latam_use_documents)
    if con_docs:
        registrar('0.9', 'ok', 'bloqueante', 'Diarios de venta con documentos SUNAT',
            str(len(con_docs)) + ' de ' + str(len(diarios_venta)) + ' diarios de venta usan tipos de documento: ' + ', '.join(con_docs.mapped('name')) + '.')
    else:
        registrar('0.9', 'falta', 'bloqueante', 'Diarios de venta con documentos SUNAT', 'Ningun diario de venta tiene activado "usar documentos". Sin eso no hay facturas/boletas SUNAT.')
    tiene_banco = env['account.journal'].search_count([('type', '=', 'bank')])
    if not tiene_banco:
        registrar('0.9b', 'falta', 'importante', 'Diario bancario', 'No hay ningun diario tipo banco. Se necesita para registrar cobros y conciliar.')

    # 0.10 plan de cuentas
    n_cuentas = env['account.account'].search_count([])
    if n_cuentas >= 50:
        registrar('0.10', 'ok', 'bloqueante', 'Plan de cuentas', str(n_cuentas) + ' cuentas cargadas (PCGE).')
    else:
        registrar('0.10', 'falta', 'bloqueante', 'Plan de cuentas', 'Solo ' + str(n_cuentas) + ' cuentas. El PCGE trae cientos; la localizacion no cargo bien.')

# ---------- FASE 1: DATOS MAESTROS ----------
if alcance_txt in ('completo', 'datos_maestros'):
    Prod = env['product.template']
    prods = Prod.search([('sale_ok', '=', True), ('active', '=', True)])
    if prods:
        sin_unspsc = prods.filtered(lambda p: not p.unspsc_code_id)
        sin_imp = prods.filtered(lambda p: not p.taxes_id)
        if not sin_unspsc and not sin_imp:
            registrar('1.1', 'ok', 'bloqueante', 'Productos completos', str(len(prods)) + ' productos vendibles con UNSPSC e impuesto.')
        else:
            registrar('1.1', 'parcial', 'bloqueante', 'Productos completos',
                str(len(sin_unspsc)) + ' de ' + str(len(prods)) + ' sin codigo UNSPSC, ' + str(len(sin_imp)) + ' sin impuesto de venta. SUNAT exige UNSPSC. Ejemplos sin UNSPSC: ' + ', '.join(sin_unspsc[:5].mapped('name')) + '.')
    else:
        registrar('1.1', 'falta', 'bloqueante', 'Productos', 'No hay productos vendibles cargados.')

    Partner = env['res.partner']
    clientes = Partner.search([('customer_rank', '>', 0), ('is_company', '=', True)])
    if clientes:
        sin_doc = clientes.filtered(lambda c: not c.vat or not c.l10n_latam_identification_type_id)
        sin_dir = clientes.filtered(lambda c: not c.street)
        if not sin_doc and not sin_dir:
            registrar('1.2', 'ok', 'importante', 'Clientes completos', str(len(clientes)) + ' clientes con documento y direccion.')
        else:
            registrar('1.2', 'parcial', 'importante', 'Clientes completos',
                str(len(sin_doc)) + ' de ' + str(len(clientes)) + ' sin tipo/numero de documento, ' + str(len(sin_dir)) + ' sin direccion. Ejemplos: ' + ', '.join(sin_doc[:5].mapped('name')) + '.')
    else:
        registrar('1.2', 'falta', 'importante', 'Clientes', 'No hay clientes cargados. Si el negocio ya opera, falta migrar la cartera.')

    proveedores = Partner.search([('supplier_rank', '>', 0), ('is_company', '=', True)])
    if proveedores:
        sin_ruc = proveedores.filtered(lambda p: not p.vat)
        if not sin_ruc:
            registrar('1.3', 'ok', 'importante', 'Proveedores completos', str(len(proveedores)) + ' proveedores con RUC.')
        else:
            registrar('1.3', 'parcial', 'importante', 'Proveedores completos', str(len(sin_ruc)) + ' de ' + str(len(proveedores)) + ' sin RUC: ' + ', '.join(sin_ruc[:5].mapped('name')) + '.')
    else:
        registrar('1.3', 'falta', 'recomendado', 'Proveedores', 'No hay proveedores cargados.')

    n_pt = env['account.payment.term'].search_count([])
    registrar('1.6', 'ok' if n_pt >= 2 else 'parcial', 'recomendado', 'Condiciones de pago', str(n_pt) + ' condiciones definidas.' + ('' if n_pt >= 2 else ' Definir al menos contado y credito.'))

    # 1.5 migracion: no se puede automatizar, se marca como "a conversar"
    n_facturas = env['account.move'].search_count([('move_type', 'in', ('out_invoice', 'in_invoice')), ('state', '=', 'posted')])
    n_quants = env['stock.quant'].search_count([('quantity', '>', 0)])
    registrar('1.5', 'a_conversar', 'bloqueante', 'Migracion de datos iniciales',
        'Hoy hay ' + str(n_facturas) + ' facturas contabilizadas y ' + str(n_quants) + ' posiciones de stock. Preguntar al dueno: saldos iniciales, deudas abiertas y stock inicial, estan cargados o faltan?')

# ---------- FASE 2: OPERATIVO ----------
if alcance_txt in ('completo', 'operativo'):
    n_etapas = env['crm.stage'].search_count([])
    registrar('2B', 'ok' if n_etapas >= 3 else 'parcial', 'recomendado', 'Etapas CRM', str(n_etapas) + ' etapas de pipeline.' + ('' if n_etapas >= 3 else ' Definir las del flujo real.'))

    n_alm = env['stock.warehouse'].search_count([])
    registrar('2D', 'ok' if n_alm >= 1 else 'falta', 'importante', 'Almacenes', str(n_alm) + ' almacen(es) configurado(s).')

    n_reglas = env['stock.warehouse.orderpoint'].search_count([])
    registrar('2C', 'ok' if n_reglas >= 1 else 'parcial', 'recomendado', 'Reglas de reabastecimiento', str(n_reglas) + ' reglas. ' + ('' if n_reglas else 'Sin reglas no hay compras automaticas.'))

    if 'account_followup.followup.line' in env:
        n_niv = env['account_followup.followup.line'].search_count([])
        registrar('2E.7', 'ok' if n_niv >= 1 else 'falta', 'importante', 'Niveles de seguimiento de cobranza',
            str(n_niv) + ' niveles. Verificar a mano que las plantillas cumplan INDECOPI (transparencia, max 1 contacto/dia, 7:00-20:00 L-S, sin terceros).')
    else:
        registrar('2E.7', 'falta', 'importante', 'Seguimiento de cobranza', 'Modulo de seguimientos no instalado.')

    # Se lee via la compania (accesible sin sudo -- la convencion del
    # catalogo prohibe sudo fuera de la guarda). Sin getattr (no existe
    # en el sandbox).
    usa_credito = env.company.account_use_credit_limit if 'account_use_credit_limit' in env.company._fields else False
    registrar('2E.5', 'ok' if usa_credito else 'parcial', 'recomendado', 'Limite de credito por cliente',
        'Activado.' if usa_credito else 'No activado. Habilitar en Contabilidad > Ajustes > Facturas al cliente si el negocio vende a credito.')

# ---------- RESUMEN ----------
bloq = [h for h in hallazgos if h['prioridad'] == 'bloqueante' and h['estado'] in ('falta', 'parcial')]
imp = [h for h in hallazgos if h['prioridad'] == 'importante' and h['estado'] in ('falta', 'parcial')]
conv = [h for h in hallazgos if h['estado'] == 'a_conversar']
oks = [h for h in hallazgos if h['estado'] == 'ok']

if bloq:
    veredicto = 'NO LISTA: ' + str(len(bloq)) + ' vacio(s) bloqueante(s).'
elif imp:
    veredicto = 'OPERABLE CON RESERVAS: sin bloqueantes, ' + str(len(imp)) + ' vacio(s) importante(s).'
else:
    veredicto = 'LISTA segun la norma (checks automaticos).'

ai['result'] = {
    'ok': True,
    'mensaje': veredicto + ' ' + str(len(oks)) + ' checks OK de ' + str(len(hallazgos)) + '. ' +
               (str(len(conv)) + ' punto(s) requieren conversar con el dueno.' if conv else ''),
    'datos': {
        'alcance': alcance_txt,
        'veredicto': veredicto,
        'bloqueantes': bloq,
        'importantes': imp,
        'a_conversar': conv,
        'ok': [h['id'] + ' ' + h['titulo'] for h in oks],
        'recomendados_pendientes': [h for h in hallazgos if h['prioridad'] == 'recomendado' and h['estado'] in ('falta', 'parcial')],
    },
}
'''

CODIGO = GUARDA_TEMPLATE + "\n" + CUERPO
