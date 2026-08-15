# Booster — carcasa (addon Odoo)

Módulo instalable en el tenant: menús, wizard conversacional (5 fases), registro
`x_booster_implementacion` (estado persistente del wizard) y `x_booster_licencia`
(llave). CERO lógica de negocio — las recetas viven en el Servidor de Control.

Spec: `../../Agentes_SAAS/agentes_v2/01-booster-implementador.md` + RFD v2.9 §4.

Estructura Odoo pendiente de armar aquí:
- `__manifest__.py` · `models/` (x_booster_licencia, x_booster_implementacion)
- `wizard/` (fases 1-5) · `security/` (grupos por perfil, Fase 3)
