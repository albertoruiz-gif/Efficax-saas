# Efficax SaaS — Odoo + Agentes IA

Monorepo del producto Efficax Agents: Servidor de Control, carcasa Booster,
Server Actions de los agentes y bases de conocimiento.

**Especificación fuente de verdad:** `../Agentes_SAAS/RFD_Efficax_SaaS_Odoo_Agentes_v2.9.md`
y las specs por agente en `../Agentes_SAAS/agentes_v2/`. El código es un
subproducto de la especificación, no al revés (E-SDD — ver `CONSTITUTION.md`).

## Componentes

| Carpeta | Qué es | Stack |
|---|---|---|
| `servidor_control/` | Capa técnica externa: tabla de tenants, ciclo diario de llaves (dead man's switch), Supervisor de Implementación, microservicios (WhatsApp, fallback IA) | Python 3.11+ / FastAPI |
| `booster/` | Carcasa instalada en cada tenant Odoo — menús, wizard, guardas. Cero lógica de negocio | Addon Odoo (Python) |
| `server_actions/` | Las 49 herramientas de los agentes como plantillas Python con guarda de llave; generador desde el catálogo JSON | Python |
| `scripts/` | Utilitarios de operación y auditoría (killswitch, validaciones) | Python |
| `kb/` | Bases de conocimiento por país: contratos (10 tipos), jurisprudencia, tributario | Markdown/JSON |
| `docs/` | Metodología, DevSecOps y especificaciones formales (SPEC-XXX) | Markdown |

## Arranque rápido (desarrollo)

```bash
cd servidor_control
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
pytest                       # suite completa
ruff check .                 # lint
uvicorn app.main:app --reload
```

## Reglas de oro (resumen — el contrato completo es CONSTITUTION.md)

1. Nada se programa sin especificación o decisión registrada del dueño del producto.
2. Ningún secreto toca el repo (gitleaks lo verifica en CI).
3. Toda regla crítica (dinero, llaves, datos de tenant) tiene test propio en el mismo commit.
4. Conventional Commits: `feat:`, `fix:`, `test:`, `docs:`, `chore:` (+ épica si aplica).
5. `git push` a `main` solo con confirmación explícita de Alberto.
