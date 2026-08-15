# CONSTITUTION — Contrato operativo del proyecto Efficax SaaS

Versión ligera de E-SDD (Spec-Driven Development de Efficax), heredada de la
práctica real del proyecto Haskell (`ESTRUCTURA_GITHUB_Y_METODOLOGIA.md`).
Si otro documento contradice a este, gana este — y se actualiza aquí primero.

## 1. Principio rector

> La especificación es la fuente de verdad. El código es un subproducto de la
> especificación, no al revés.

Las especificaciones viven en `../Agentes_SAAS/` (RFD v2.9 + specs por agente +
catálogo JSON de 49 herramientas). Antes de programar algo grande o con reglas
de negocio no triviales: presentar opciones concretas con recomendación y pedir
la decisión puntual a Alberto. La decisión queda registrada (chat + spec).

## 2. Tres niveles de autonomía

**✅ Siempre, sin preguntar:**
- Correr `ruff check` y la suite completa de `pytest` antes de dar un cambio por terminado.
- Crear/actualizar tests de toda regla crítica en el mismo cambio.
- Actualizar `docs/` y las specs cuando la implementación revele que el plan estaba incompleto.
- `git status` antes de todo `git add` — nunca `git add -A` a ciegas.

**⚠️ Preguntar primero:**
- Agregar o actualizar dependencias (`requirements*.txt`).
- Cambios de esquema de datos que afecten datos existentes; migraciones destructivas.
- Modificar el pipeline CI (`.github/workflows/`).
- Cambiar una regla de negocio ya implementada sin registrarla antes en la spec.
- Tocar credenciales, llaves de tenants o cualquier cosa de un tenant en producción.
- Cualquier `git push` a `origin/main`.

**🚫 Nunca:**
- Subir secretos, llaves o credenciales al repo (gitleaks verifica; `.gitignore` cubre).
- Borrar o comentar un test que falla para poder avanzar.
- Ignorar un error de tipo o advertencia del linter.
- Ejecutar acciones contra el Odoo real de un cliente desde desarrollo — los
  ambientes de desarrollo apuntan SOLO a instancias de prueba (lección Haskell 2026-08-14).

## 3. Invariantes de negocio con nombre (protegidas por tests)

- **"Sin llave vigente, ninguna Server Action ejecuta"** — la guarda Booster es
  fail-closed: llave ausente o > 48h = servicio suspendido. Test: `test_guarda_llave.py`.
- **"El Servidor de Control jamás renueva la llave de un tenant moroso"** — la
  renovación exige estado de pago al día. Test en `servidor_control/tests/`.
- **"Nada se borra en un tenant que ya operó"** — cancelación = desactivar/archivar
  (3 capas), borrado solo si nunca operó (regla aprobada 2026-08-14).
- **"company_id explícito, fail-closed"** — ninguna conexión API asume compañía.
- **"IDs jamás inventados"** — búsqueda sin resultado = `ok:false`, nunca ID en 0.

## 4. Commits (Conventional Commits)

`feat:`, `fix:`, `test:`, `docs:`, `chore:` — con la épica/agente si aplica:
`feat(booster): wizard fase 1-bis checklist de detección`. El cuerpo explica el
PORQUÉ (no solo el qué) y qué verificación se corrió (`pytest 12/12 verde, ruff limpio`).

## 5. Especificaciones formales

Funcionalidad nueva no trivial → `docs/specs/SPEC-XXX-nombre.md` ANTES del código
(plantilla en `docs/specs/SPEC-000-plantilla.md`). La spec se aprueba en el chat
con Alberto y el commit de código la referencia.
