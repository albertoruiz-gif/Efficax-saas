"""GUARDA BOOSTER — plantilla canónica que encabeza TODA Server Action instalada.

No remover (incumplimiento de contrato). Fuente: RFD v2.9 RF-15 y
00-README-agentes-v2.md. La lógica testeable equivalente vive en
servidor_control/app/llaves/renovacion.py (llave_vigente).

VALIDADO EN VIVO en el Odoo de Efficax el 15-ago-2026 (tenant 0):
- llave fresca  -> la herramienta ejecuta y escribe en la base (lead creado).
- llave > 48h   -> UserError, la herramienta NO ejecuta y no se escribe nada.

CORRECCIÓN IMPORTANTE (bug real, detectado en esa prueba): la versión previa
de esta plantilla usaba `datetime.now()`, que NO existe en el sandbox de
Odoo — ahí `datetime` es un `wrap_module`, así que hay que escribir
`datetime.datetime.now()`. Con la forma anterior, las 58 herramientas
habrían fallado en su primera línea.
"""

# Builtins que el sandbox de Odoo (safe_eval) NO expone y que por lo tanto
# no se pueden usar en el `code` de una Server Action. Verificado a mano:
# `type` lanza NameError. Ante la duda, probar antes de asumir.
BUILTINS_NO_DISPONIBLES = ("type", "open", "__import__", "eval", "exec", "compile")

GUARDA_TEMPLATE = '''# GUARDA BOOSTER — no remover (incumplimiento de contrato)
lic = env['x_booster_licencia'].sudo().search([], limit=1)
if not lic or (datetime.datetime.now() - lic.x_fecha_renovacion).total_seconds() > 172800:  # 48h
    raise UserError('Servicio suspendido — contacta a Efficax (soporte@efficaxba.com)')
'''
