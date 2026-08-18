# UX de onboarding — cómo llega un cliente real a Booster

Vacío detectado el 17-ago-2026 (Alberto, viendo la lista técnica de
`x_booster_implementacion` en el backend de Odoo): **no existe todavía un
diseño de cómo un cliente prospecto llega, interactúa y avanza con
Booster.** Lo que sí existe (Fase 1, probada en vivo) asume que quien le
habla a Booster YA tiene una sesión de Odoo abierta — cierto para mí
probando, falso para un prospecto real que todavía no es cliente.

Este documento es el diseño propuesto. No cambia código — es la base
para decidir qué construir en Fase 3 (Provisioning) y ajustar Fase 1/2.

## Lo que el cliente NUNCA debe ver

La lista/formulario de `x_booster_implementacion` en el backend de
Odoo (Ajustes → Técnico, o el menú "Booster" tal cual se ve hoy) es una
vista de depuración para Efficax, generada automáticamente por Odoo para
cualquier modelo custom. No tiene diseño, muestra campos crudos
(`x_respuestas_json` como texto plano), y **no debe estar en el camino
de ningún cliente.** El menú "Booster" que aparece en el grid de apps
hoy es correcto como acceso RÁPIDO para Efficax (QA), pero la interfaz
real del cliente es, y debe seguir siendo, 100% conversacional — el
chat del agente, nunca una lista de Odoo.

## El problema real: el huevo y la gallina

Fase 1 de Booster (Descubrimiento) ya funciona conversando por el chat
de un agente de IA — pero ese chat vive DENTRO de una base de datos
Odoo. Un prospecto que todavía no es cliente **no tiene ninguna base de
datos Odoo todavía.** No existe manera de que "hable con Booster" antes
de que exista un tenant donde Booster viva. Ese es el vacío que hay que
cerrar.

## Propuesta: reusar el trial nativo de Odoo como punto de entrada

Este mismo Odoo de Efficax (`efficaxba-online`) tiene instalado
`saas_trial` (confirmado con `ir.module.module`, state='installed') --
el mecanismo con el que Odoo Online genera bases de datos nuevas y
vacías en minutos, sin tarjeta, cuando alguien pide "probar Odoo". Es
exactamente el mecanismo que YA creó la base de datos que estamos
usando. Reusarlo evita construir infraestructura de provisioning propia
para algo que Odoo ya resuelve.

**Flujo propuesto:**

```
1. DESCUBRIMIENTO (hoy: nada construido para esto)
   Prospecto ve un CTA ("Prueba Booster gratis") en Casa Efficax
   (marketing/checkout, fuera de este repo) o en cualquier canal de
   adquisición (WhatsApp, redes, referido).
        |
        v
   Click dispara el trial nativo de Odoo -> nace un tenant NUEVO y
   VACÍO en un par de minutos (mismo mecanismo saas_trial). Este
   tenant, si el prospecto convierte, ES el tenant real -- no hay
   migración de datos de "prueba" a "definitivo" despues.
        |
        v
   Primer login: el ÚNICO app visible es Booster (política ya
   decidida: agentes/herramientas invisibles en tenants de cliente).
   El chat de Booster se abre automáticamente (o es el único botón
   posible en pantalla) -- cero fricción de "encontrar el ícono de IA".
        |
        v
   Booster arranca Fase 1 (Descubrimiento) -- YA CONSTRUIDA Y
   PROBADA: país, industria, qué vende, datos legales, régimen fiscal,
   roles de usuarios, dolores del negocio. Guarda avance
   incrementalmente (x_booster_implementacion, ya funciona -- el bug
   de continuidad por x_dueno_email ya está resuelto).

2. PROPUESTA / CHECKOUT (Fase 2 -- fuera de este repo, spec en
   Casa Efficax)
   En un punto natural (discovery "suficiente" -- criterio a definir
   con el spec de Casa Efficax), Booster resume lo aprendido y deriva
   al checkout: el prospecto ve QUÉ le conviene (agentes/plan) y paga
   ANTES de que se instale nada técnico (regla ya acordada esta
   sesión).

3. PROVISIONING (Fase 3 -- no construida)
   Post-pago, Booster sigue en el MISMO tenant (no hay tenant nuevo
   que crear -- ya existe desde el paso 1) y retoma la conversación
   con las respuestas de Fase 1 ya guardadas. Ahí es cuando pide,
   en un solo checkpoint, TODOS los accesos que va a necesitar (ver
   checklist ya documentado más abajo en este mismo README de
   Booster) -- nunca antes.

4. AJUSTES / SOPORTE CONTINUO (Fases 4-5)
   El cliente sigue hablando con Booster para pedir agentes nuevos
   (upgrade), ajustar KPIs, etc. -- mismo canal desde el día 1, sin
   aprender una interfaz nueva.
```

## Por qué este orden y no otro

- **Cero fricción de "cómo empiezo":** no hay que crear cuenta, elegir
  plan, ni pagar ANTES de poder hablar con alguien (aunque sea una IA)
  que entienda el negocio. Baja la barrera de entrada al mínimo posible
  con lo que Odoo ya ofrece gratis.
- **Un solo tenant, nunca dos:** evita el trabajo (y el riesgo de
  bugs) de migrar datos de un tenant "de prueba" a uno "definitivo".
  El trial ES el tenant real si convierten.
- **Consistente con la política ya decidida:** agentes/herramientas
  invisibles en tenants de cliente, solo Booster visible -- este flujo
  no la contradice, la usa desde el primer segundo.
- **No inventa infraestructura nueva:** usa `saas_trial`, que Odoo
  Online ya opera y ya demostró funcionar (es como nació este mismo
  tenant). No hay que construir ni mantener un sistema de
  provisioning propio para esta parte.

## Lo que falta decidir (no técnico, de producto)

1. **¿El chat se abre automáticamente al primer login, o el cliente
   tiene que hacer un primer click?** Auto-abrir reduce fricción pero
   puede sentirse invasivo; un botón único y obvio ("Habla con
   Booster") es más predecible. Recomendación: auto-abrir con un
   mensaje de bienvenida corto, no un formulario -- se siente a
   conversación, no a wizard.
2. **¿Qué pasa si el prospecto abandona a mitad de Fase 1?** Hoy no
   hay ningún recordatorio ni seguimiento -- el registro
   `x_booster_implementacion` queda ahí, sin que nadie lo note. Un
   `ir.cron` simple (mismo patrón ya usado en `dashboard_kpis/alerta_umbral.py`)
   podría avisar a Efficax ("prospecto sin actividad 48h en Fase 1")
   para que alguien retome manualmente -- no es urgente, pero es
   barato de construir cuando se decida.
3. **¿Cuál es el criterio de "discovery suficiente" para pasar a
   Fase 2?** Hoy Booster no tiene ninguna regla de cuándo ofrecer el
   checkout -- depende del spec de Casa Efficax, fuera de este repo.

## Qué NO cambia por este documento

Este es un diseño, no una implementación. No se tocó código de
Booster ni de Casa Efficax al escribirlo. Cuando se decida construir
Fase 3, este documento es el punto de partida.
