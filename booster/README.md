# Booster — carcasa (addon Odoo)

Módulo instalable en el tenant: menús, wizard conversacional (5 fases), registro
`x_booster_implementacion` (estado persistente del wizard) y `x_booster_licencia`
(llave, vive en `server_actions/guarda_llave.py` + `scripts/booster_rpc.py`).
CERO lógica de negocio — las recetas viven en el Servidor de Control.

Spec: `EFFICAX_IA/Agentes_SAAS/agentes_v2/01-booster-implementador.md` (fuera de
este repo, ver `server_actions/README.md` sobre esta dependencia cross-repo) +
RFD v2.9 §4.

## Por qué no es un addon con `__manifest__.py` (decisión, no olvido)

El plan original era un addon Odoo instalable de verdad. Se descartó
(16-ago-2026) tras verificar en vivo que `efficaxba-online.odoo.com` es
**Odoo Online estándar** (confirmado: módulos `saas_trial`/`saas_ai`
instalados, sin ningún parámetro de Odoo.sh, y sin proyecto en odoo.sh
asociado a la cuenta) — Odoo Online no permite instalar código Python
custom, solo Odoo.sh o self-hosted lo permiten. Si en algún momento se migra
a Odoo.sh, ese es el momento de reconstruir esto como addon real con
`__manifest__.py`.

En su lugar, Booster se construye con el mismo mecanismo que el resto del
catálogo: modelos vía `ir.model` (`state='manual'`), lógica vía
`ir.actions.server`, y un menú/ícono de app vía `ir.ui.menu` +
`ir.actions.act_window` — es exactamente lo que usa Odoo Studio por dentro.

## Estado actual (16-ago-2026)

**Fase 1 (Descubrimiento) instalada y probada en vivo** en el tenant de
Efficax (`efficaxba-online.odoo.com`), visible como app "Booster" en el
grid de apps:

- Modelo `x_booster_implementacion`: negocio, dueño/email, fase actual,
  respuestas de la entrevista (JSON, se van fusionando), checkpoints,
  pendientes.
- Server Action `booster: guardar_avance_wizard`
  (`implementaciones/guardar_avance_wizard.py`) — con la guarda de licencia
  igual que cualquier otra herramienta del catálogo.
- Agente conversacional **Booster** (GPT-5, estilo balanced,
  restringido a fuentes) con el tema "Fase 1: Descubrimiento".
- Instalador reproducible: `instalar_booster_fase1.py` — idempotente,
  correrlo de nuevo no duplica nada. Es el que hay que extender cuando se
  construyan las Fases 2-5.

**Fases 2-5: no construidas todavía.** El agente lo sabe y lo dice
explícitamente si el dueño pregunta — no promete continuar solo.

## Ícono de la app (16-ago-2026, iterado dos veces)

Se reemplazó el ícono genérico inicial (fa-rocket morado, placeholder) por
uno propio, en el naranja `#FF6A00` y negro `#050505` exactos de
`BrandBook_Efficax_Premium_Completo_v3.docx` (Branding, fuera de este
repo). Nombre y branding de Booster **no están decididos como
definitivos** — puede cambiar más adelante — así que el ícono se hizo
simple y reemplazable, no una inversión grande de diseño.

**Intento 1 (descartado):** una celda Braille con los puntos 1 y 2
encendidos (letra "B"). La idea de usar Braille la propuso Alberto y
encaja bien con el propio isotipo de Efficax (construido con puntos y
barras) — pero la ejecución no funcionó visualmente ("se ve horrible",
feedback directo). Descartada.

**Intento 2 (también descartado):** reconstruir la letra B con el MISMO
sistema modular de barras/puntos que arma E-F-F-I-C-A-X en el logo real
(medido con precisión de píxel sobre `image1.png` del brand book: grosor
de barra, radio de esquina, espaciado entre filas, todo proporcional).
Se probaron 3 variantes — asta + 3 barras conectadas (se leía como "E"),
asta + verticales cerrando los dos vientres (quedaba un bloque sólido
pesado, no encajaba con el resto de letras que son livianas y separadas),
y la construcción de la "C" con la abertura cerrada (se leía como una
simple lista de viñetas, no como letra). Conclusión: ese sistema de
letras se diseñó para deletrear EFFICAX específicamente, no es un
alfabeto completo — no da para una B legible sin forzarlo demasiado.

**Versión actual:** letra "B" geométrica real, tipografía Montserrat
Black (peso grueso, redondeada, misma familia visual que Inter/Manrope —
las que pide el brand book para UI digital, pero no están instaladas en
esta máquina; Montserrat es el sustituto más cercano disponible),
naranja sobre negro. Prioriza que se lea claro como "B" por sobre imitar
la construcción exacta del logotipo.

Fuente: `booster/assets/icono_booster_b.png` (generado con Pillow, no a
mano en un editor — reproducible). Instalado vía `web_icon_data` en
`ir.ui.menu` (campo binario para ícono custom, no el `web_icon` de texto
que solo acepta el formato `fa-icono,#fondo,#icono`). **Detalle no
documentado por Odoo, verificado en vivo:** si `web_icon_data` y
`web_icon` se escriben en la misma llamada `write()`, Odoo vacía
`web_icon_data` — hay que escribirlos en llamadas separadas (así quedó en
`instalar_booster_fase1.py`).

## Bug real encontrado y corregido (16-ago-2026)

La primera versión de `guardar_avance_wizard.py` usaba `x_tenant` como
llave para saber si ya existía un registro de esa implementación y
continuarlo. Eso partió el wizard en DOS registros en la primera prueba
real: uno con un placeholder ("Pendiente - nombre del negocio") del primer
mensaje, porque el nombre del negocio **todavía no se conocía** — es
justo lo que Fase 1 va descubriendo — y otro nuevo una vez que sí se supo,
sin fusionarse nunca. Corregido usando `x_dueno_email` como llave: se
conoce desde el primer mensaje y no cambia durante la conversación.
Re-probado con la conversación completa: un solo registro, correctamente
fusionado.

## Visibilidad en tenants de clientes (pendiente de construir)

Decisión de Alberto (16-ago-2026): en el tenant de **Efficax** los agentes/
herramientas quedan visibles (es donde se confirma instalación y se afinan).
En tenants de **clientes reales**, deben quedar invisibles/tras bambalinas —
solo Booster visible — pero su estado operativo debe poder confirmarse por
telemetría y por el propio Booster. Esto todavía no está construido (no
existe ningún tenant de cliente real todavía); queda para cuando se diseñe
el mecanismo de provisioning de Fase 3.

## Modelo de negocio (acordado 16-ago-2026)

El contrato/carrito se cierra en **Fase 2** (checkout en Casa Efficax, ya
en el spec) — el cliente sabe qué paga ANTES de que Booster instale nada
técnico. Fase 3 solo instala lo que ese contrato dice. Si en operación pide
más agentes, es un **upgrade**: mismo mecanismo de instalación, disparado
por el lazo Mentor→Booster, registrado para facturación adicional — no un
camino nuevo.

## Servidor de Control (hasta que haya volumen de clientes)

Por ahora, **no hay una API de Servidor de Control corriendo** — el rol lo
cumple manualmente quien implementa (mismo patrón de `scripts/booster_rpc.py`
usado toda la noche del 15/16-ago para instalar y probar las 9 herramientas
de `ventas_atencion` y esta primera pieza de Booster). Todo el proceso queda
documentado y versionado acá para poder migrar a una API real más adelante
sin perder el conocimiento acumulado.

## Estructura

- `implementaciones/` — código real de las Server Actions de Booster (mismo
  patrón que `server_actions/implementaciones/`, doble prueba obligatoria:
  vigente + kill-switch).
- `instalar_booster_fase1.py` — instalador idempotente de la Fase 1.
- Pendiente de armar: Fases 2-5, y — solo si se migra a Odoo.sh —
  `__manifest__.py` / `models/` / `wizard/` / `security/` reales.
