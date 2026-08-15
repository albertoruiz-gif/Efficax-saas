"""GUARDA BOOSTER — plantilla canónica que encabeza TODA Server Action instalada.

No remover (incumplimiento de contrato). Fuente: RFD v2.9 RF-15 y
00-README-agentes-v2.md. La lógica testeable equivalente vive en
servidor_control/app/llaves/renovacion.py (llave_vigente).
"""

GUARDA_TEMPLATE = '''# GUARDA BOOSTER — no remover (incumplimiento de contrato)
lic = env['x_booster_licencia'].sudo().search([], limit=1)
if not lic or (datetime.now() - lic.x_fecha_renovacion).total_seconds() > 172800:  # 48h
    raise UserError('Servicio suspendido — contacta a Efficax (soporte@efficaxba.com)')
'''
