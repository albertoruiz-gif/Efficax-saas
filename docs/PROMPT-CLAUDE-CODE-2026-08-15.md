Lee primero `docs/HANDOFF-2026-08-15.md` (ruta completa: `C:\Users\Lenovo ideaPad\Desktop\Efficax-saas\docs\HANDOFF-2026-08-15.md`) — ahí está todo el contexto de la sesión anterior: arquitectura probada en vivo contra Odoo, 3 bugs corregidos, y el estado actual del catálogo de 58 herramientas (1 implementada y probada: `crear_actualizar_lead`).

Con ese contexto, hazme esto en orden:

## 1. Push de los 3 commits pendientes

`origin/main` está en `482d25b`. Hay 3 commits locales sin subir:
- `351497b` — generador.py reescrito + agente inventarios agregado al catálogo (51→58 herramientas)
- `1d4af37` — fix de patrón wildcard en `.gitignore`
- `3188487` — implementación real de `crear_actualizar_lead` + `esquemas_odoo.py` + fix `guarda_llave.py`

Verifica que el árbol de trabajo esté limpio, corre los tests (`pytest`) y el lint (`ruff`) antes de subir, y haz el push a `main`.

## 2. Limpieza de carpetas residuales

Borra las carpetas `.git_roto_borrar*` en la raíz del repo (son residuos de un workaround al bug de bloqueo de `.git` que tenía Cowork en la carpeta montada de Windows — ya no hacen falta).

## 3. Confirmar seguridad

Recuérdame explícitamente que debo revocar/regenerar el Personal Access Token de GitHub que quedó expuesto en el chat de Cowork (visto en texto plano y en una captura) — no se usó para nada, pero hay que invalidarlo.

## 4. Seguir con la implementación de herramientas

Una vez el repo esté limpio y pusheado, seguimos escribiendo la lógica real de las 57 herramientas restantes del catálogo (`herramientas_esquemas.json`), con la misma prueba doble que se estableció (`implementaciones/README.md`): vigente (camino feliz) + llave vencida (kill-switch), instalado y probado en vivo contra el Odoo de Efficax.

Prioridad: terminar Ventas & Atención 24/7 (quedan 8 de 9), después Mentor, después el resto por agente.

Sigue las convenciones documentadas en el handoff: guarda de licencia siempre primero, `datetime.datetime.now()` (nunca `datetime.now()`), nunca `sudo()` fuera de la guarda, variables del esquema saneado (`esquemas_odoo.py`) no del catálogo, y todo lo que el esquema ya no valida se valida a mano en el código.

No toques por ahora: Legal & Contratos, Field Service, ni la estrategia país por país en LatAm — están explícitamente en pausa.
