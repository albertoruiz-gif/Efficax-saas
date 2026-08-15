# DevSecOps — Efficax SaaS

Pipeline y prácticas heredadas del proyecto Haskell, adaptadas a Python.

## Pipeline CI (`.github/workflows/ci.yml`) — dispara en push y PR a main

| Job | Herramienta | Qué bloquea |
|---|---|---|
| `lint` | ruff | Errores de estilo/calidad |
| `tests` | pytest | Test que falla |
| `sast` | CodeQL (python) + bandit | Vulnerabilidad de código |
| `sca` | pip-audit | Dependencia con CVE alto/crítico |
| `secret-scan` | gitleaks | Credencial en el diff |
| `imagen` | Trivy | (Se activa cuando existan Dockerfiles) CVE crítico/alto en imagen |

## Reglas de runtime (fail-closed, lección Haskell)

- Secretos SIN valor por defecto: si falta la variable de entorno, la app NO arranca.
- `config.py` centraliza todo secreto (env vars en dev; AWS Secrets Manager en producción).
- Producción es el único ambiente que toca instancias Odoo reales de clientes.
- Toda acción sobre un tenant queda en el inventario (auditoría, rollback, kill-switch).

## Auditoría

- Auditorías periódicas con hallazgos concretos y escenario de falla específico
  (patrón auditoría Haskell 2026-08-10), cada corrección verificada en vivo.
- El historial git es la bitácora: commits con porqué + verificación ejecutada.
