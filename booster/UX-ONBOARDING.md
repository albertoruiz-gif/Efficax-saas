# UX de onboarding — cómo llega un cliente real a Booster

Vacío detectado el 17-ago-2026 (Alberto, viendo la lista técnica de
`x_booster_implementacion` en el backend de Odoo): faltaba conectar
"cómo llega un prospecto a Booster antes de tener Odoo" con lo que el
spec de Booster (`EFFICAX_IA/Agentes_SAAS/agentes_v2/01-booster-implementador.md`,
cross-repo) YA define en detalle para las fases 1-4. Esta v2 del
documento corrige eso: lo que sigue está basado en ese spec, no
inventado — donde algo no está resuelto ahí, se marca explícito como
pendiente de decisión de Alberto.

Este documento sigue siendo diseño, no código.

## Lo que el cliente NUNCA debe ver

La lista/formulario de `x_booster_implementacion` en el backend de
Odoo es una vista de depuración para Efficax, generada automáticamente
por Odoo para cualquier modelo custom — no tiene diseño, muestra campos
crudos. **No debe estar en el camino de ningún cliente.** La interfaz
real es 100% el chat de Booster.

## El problema del huevo y la gallina

Fase 1 de Booster ya funciona conversando por chat — pero ese chat vive
DENTRO de una base de datos Odoo. Un prospecto que todavía no es
cliente no tiene ninguna base de datos Odoo todavía.

**Propuesta (sin cambios respecto a v1):** reusar `saas_trial` (ya
instalado en este mismo tenant, mismo mecanismo que lo creó) para que
un clic en "Prueba Booster gratis" genere un tenant nuevo y vacío en
minutos, sin tarjeta. Si el prospecto convierte en Fase 2, ES el mismo
tenant el que sigue — nunca hay migración de "prueba" a "definitivo".

**Corrección sobre v1 (punto de Alberto):** ese primer clic no debería
activar SOLO el SaaS de Odoo — debería disparar la activación de los
demás servicios que Booster va a necesitar desde el arranque, según el
checklist YA documentado más abajo en este mismo README de Booster
("Requisito de diseño: TODOS los accesos se piden UNA sola vez"). Cuáles
de esos servicios pueden activarse en modo trial/sandbox en el momento
del clic (vs. cuáles requieren datos reales del negocio y por lo tanto
esperan a Fase 3) es una decisión pendiente, servicio por servicio — no
se resuelve acá con una lista inventada.

## Los TRES caminos reales de Fase 1 (no dos) — ya definidos en el spec

Alberto preguntó por "nuevos vs. antiguos, y un tercero". El spec de
Booster ya distingue **tres** caminos, no dos, y el punto donde cada uno
pide qué datos está definido:

### A. Cliente nuevo — sin operación previa

No hay saldos, catálogo ni clientes que migrar. Fase 1 es puramente
cualitativa: país/moneda → régimen fiscal → industria/qué vende →
usuarios y roles → ¿dominio/correo? → dolores top-3. Fase 3
(post-checkout) provisiona un tenant limpio; el cliente crea sus
primeros productos/clientes con ayuda de Booster **mientras opera**, no
como una carga masiva previa.

### B. Cliente que ya opera, pero SIN Odoo (Excel, otro sistema, papel)

Misma Fase 1 cualitativa, más una pregunta de spec ya definida: **Fase
2 — "Propuesta y datos"** entrega **plantillas** (productos, clientes,
saldos de apertura, proveedores — campos base Odoo) y **valida antes de
importar** (SKU duplicados, RUC malformados, asiento de apertura
cuadrado), reportando errores en lenguaje simple. La importación real
ocurre recién en **Fase 3**, después del checkout — nunca antes de que
el cliente haya pagado.

### C. Cliente que YA TIENE Odoo funcionando

Camino distinto por completo — **Fase 1-bis**, ya especificada: se
ejecuta sobre una copia **staging** (nunca producción directa: si está
en versión vieja, primero upgrade vía upgrade.odoo.com). Booster
recorre y registra "como quien inventaría una casa habitada": versión y
hosting, módulos instalados, plan contable y localización fiscal
existentes, usuarios/grupos, datos ya cargados, automatizaciones/IA
previas. **Todo lo detectado queda etiquetado "preexistente — prohibido
tocar".** Booster solo AGREGA lo que el cliente no tiene — si deja de
pagar, se apagan únicamente las piezas agregadas, y el cliente sigue
operando exactamente como antes de conocernos.

**¿Es esto lo que Alberto quiso decir con "el paquete 3"?** No estoy
seguro — puede ser este tercer camino (cliente con Odoo preexistente),
o puede ser una referencia a un plan/paquete de PRECIO (Efficax vende
"un paquete básico fijo + cargo recurrente por agente adicional", según
el RFD — no encontré una definición de "Paquete 3" como tal en el spec
cross-repo). **Pendiente de que Alberto confirme cuál de las dos cosas
es** antes de documentar más sobre eso.

## "¿Ya tiene Odoo?" es la pregunta bisagra

Fase 1 ya incluye esta pregunta explícita ("¿ya tiene dominio/correo? →
¿ya tiene Odoo? [si sí → Fase 1-bis]"). Falta agregar, en el mismo
punto, una pregunta hermana para cerrar el camino B: **si NO tiene
Odoo, ¿ya opera con datos reales en otro lado (Excel, otro sistema) que
haya que migrar, o es un negocio nuevo?** Sin esa pregunta explícita, el
flujo no sabe si ofrecer las plantillas de Fase 2 (camino B) o saltarlas
(camino A). Esto es un ajuste chico y concreto a Fase 1, no una fase
nueva.

## Por qué el checkout va ANTES de tocar algo técnico (aclarando el punto que no quedó claro en v1)

Ejemplo concreto, tomado literal del spec: Fase 2 (Propuesta y datos)
solo arma el carrito, cobra en el checkout de Casa Efficax, y —cuando
aplica (camino B)— entrega plantillas y las VALIDA. Nada de eso toca el
Odoo real del cliente todavía. Recién en **Fase 3 (Provisioning)** pasa
lo técnico de verdad: localización fiscal, plan contable, permisos por
rol, **importación de los datos ya validados**, branding, método de
pago, agentes creados, llave de licencia instalada — y Fase 3 arranca
únicamente después de que Fase 2 cerró con el pago. La razón: ni
Efficax hace trabajo técnico real (conectar bancos, migrar datos,
crear usuarios con permisos) para un prospecto que todavía podría no
convertir, ni el cliente entrega datos sensibles reales (saldos,
cartera de clientes) antes de haber decidido pagar.

## "Quiere ver que esté todo OK antes" — ya es la mejor práctica del spec (RF-20)

Para los caminos B y C (clientes que ya operan), el spec ya define el
protocolo, con nombre propio: **"Protocolo producción (RF-20 —
clientes que ya operan)"**:

```
Ensayo en copia/staging SIEMPRE
  -> aprobación del CLIENTE revisando SUS PROPIOS datos en staging
  -> backup manual
  -> ejecución en ventana de baja actividad
  -> todo aditivo (nunca se sobreescribe/borra lo existente)
  -> rollback disponible vía inventario
```

Y Fase 3 completa cierra con un **smoke test automático** antes de
darse por "implementada": el agente responde en Live Chat, el correo
transaccional sale, el método de pago carga, la llave se renovó hoy —
reporte verde/rojo al dueño y al tablero del Supervisor de
Implementación. Nada se declara listo sin ese check. Esto responde
directamente la pregunta de Alberto: el cliente que ya opera SÍ ve que
todo está OK antes de que nada cambie de verdad — es política ya
definida, solo faltaba conectarla con "cómo empieza el prospecto".

## Flujo completo (v2, corregido)

```
0. ENTRADA
   Clic en "Prueba Booster gratis" -> activa el SaaS de Odoo (saas_trial)
   Y los demás servicios del checklist que apliquen en modo trial
   (detalle pendiente, servicio por servicio).
        |
        v
1. FASE 1 -- Descubrimiento (cualitativa, ya construida)
   país/moneda -> régimen fiscal -> industria/qué vende -> usuarios y
   roles -> ¿dominio/correo? -> ¿ya tiene Odoo?
        |                                  |
        | NO                               | SI
        v                                  v
   ¿ya opera con datos reales    FASE 1-bis (staging, checklist de
   en otro lado?                 deteccion, "preexistente - prohibido
      |         |                tocar", Booster solo agrega)
      | NO      | SI                       |
      v         v                          |
   [camino A] [camino B: se anota          |
              "requiere plantillas          |
              de datos" para Fase 2]        |
      |         |                          |
      +---------+--------------------------+
        |
        v
2. FASE 2 -- Propuesta y datos
   Carrito (básico + sugeridos) -> checkout en Casa Efficax (AQUÍ se
   paga). Si camino B: entrega plantillas (productos/clientes/saldos
   apertura/proveedores) y valida antes de importar.
        |
        v
3. FASE 3 -- Provisioning (solo después del pago)
   Localización fiscal, plan contable, permisos por rol, importación de
   datos YA validados (camino B) o inventario "preexistente" respetado
   (camino C), branding, método de pago, agentes creados, llave
   instalada. Para B/C: protocolo RF-20 (staging -> aprobación del
   cliente -> backup -> ventana de baja actividad -> rollback
   disponible). Cierra con smoke test verde/rojo -- nada se da por
   implementado sin eso.
        |
        v
4. FASE 4 -- Ajustes por agente + expediente del negocio
   (ya especificado en el spec, sin cambios de este documento)
```

## Lo que sigue pendiente de decisión de Alberto

1. **Confirmar qué es "el paquete 3"** — ¿el tercer camino (cliente con
   Odoo preexistente) o un plan/precio específico no encontrado en el
   spec cross-repo?
2. Qué servicios del checklist de accesos pueden activarse en modo
   trial/sandbox desde el clic inicial, y cuáles esperan a Fase 3.
3. ¿El chat de Booster se auto-abre al primer login del trial, o
   requiere un primer clic del prospecto?
4. ¿Hay seguimiento a prospectos que abandonan a medio Fase 1 (hoy no
   hay ningún recordatorio)?
5. Criterio exacto de "discovery suficiente" para ofrecer el checkout
   de Fase 2 — el spec no lo cuantifica.

## Qué NO cambia por este documento

Sigue siendo un documento de diseño/traducción del spec existente a un
flujo de onboarding legible — no se tocó código de Booster ni de Casa
Efficax al escribirlo.
