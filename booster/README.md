# Booster — carcasa (addon Odoo)

Módulo instalable en el tenant: menús, wizard conversacional (5 fases), registro
`x_booster_implementacion` (estado persistente del wizard) y `x_booster_licencia`
(llave, vive en `server_actions/guarda_llave.py` + `scripts/booster_rpc.py`).
CERO lógica de negocio — las recetas viven en el Servidor de Control.

Spec: `EFFICAX_IA/Agentes_SAAS/agentes_v2/01-booster-implementador.md` (fuera de
este repo, ver `server_actions/README.md` sobre esta dependencia cross-repo) +
RFD v2.9 §4.

## Requisito de diseño: TODOS los accesos se piden UNA sola vez (17-ago-2026)

Detectado en carne propia esta sesión: el key de RPC de Odoo venció a
mitad de trabajo y hubo que parar para pedir uno nuevo — exactamente el
tipo de fricción tediosa y desmotivante que Booster existe para eliminar
("dejar el Odoo operando... sin consultores", spec §Naturaleza). Pedirle
al cliente credenciales/accesos de a poco, sobre la marcha, es un defecto
de diseño, no un detalle menor.

**Regla para cuando se construya la Fase 3 (Provisioning):** el wizard
tiene que levantar, en un solo checkpoint, TODO lo que Booster vaya a
necesitar durante toda la implementación — no volver a pedir nada después
salvo que el cliente agregue una capacidad nueva (upgrade). Inventario de
accesos conocidos hasta ahora que deberían pedirse juntos ahí:

- Odoo: usuario técnico + API key (idealmente sin expiración corta, o con
  renovación automatizada por el propio Servidor de Control — no manual).
- Facturación electrónica Perú: credenciales OSE/PSE (si el cliente ya
  tiene proveedor propio) o iniciar el trámite guiado (Fase 1).
- Pagos: credenciales de Mercado Pago / Culqi (recetas de Fase 3).
- Dominio/correo: acceso DNS si se va a configurar dominio propio
  (instructivos Pack 360, Fase 1).
- Marketing (si el cliente activó ese agente): códigos de píxel de
  Meta/TikTok/LinkedIn (Fase 4).

Ninguno de estos accesos existe todavía en el wizard porque la Fase 3 no
está construida — este bloque queda como checklist obligatorio para esa
fase, no como algo a resolver ahora.

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

## Norma de Implementación Odoo (19-ago-2026)

Alberto aportó el manual "Implementación del Sistema Odoo — Localización
Perú" (consultora Constanza Herrera, v1.0) con la instrucción de
complementarlo y adoptarlo como norma: Booster debe poder **seguir un
procedimiento** de implementación y **evaluar los vacíos** de un Odoo ya
andando. Quedó así:

- **`fuentes/NORMA-IMPLEMENTACION.md`** — la norma en 6 fases (Fundaciones →
  Datos maestros → Flujos operativos → Verificación → Go-live →
  Post-implementación). Cada ítem marcado `[M]` (del manual) o `[+]`
  (complemento de Efficax), y `✓auto` si la herramienta lo verifica sola.
  Los vacíos del manual que se complementaron: migración de datos
  iniciales (el más grande), inventario más allá de la guía de remisión,
  fases de verificación/go-live/post estructuradas, y el principio de
  accesos-de-una-sola-vez. Los vacíos que la norma NO cubre se declaran
  al final (RRHH, marketing, web, otras localizaciones).
- **`implementaciones/evaluar_implementacion.py`** — Server Action
  `booster: evaluar_implementacion` (id 1566): corre los 18 checks
  `✓auto` contra el Odoo real y devuelve veredicto + hallazgos por
  prioridad (bloqueante / importante / recomendado) + puntos "a
  conversar" con el dueño. Todos los modelos/campos verificados en vivo
  con `fields_get` antes de escribirla.
- **Topic "Booster — Norma de implementación"** (id 18) — agregado al
  agente con `(4, id)`, NO `(6, 0, ...)`: el instalador de Fase 1 usa
  (6,0) y habría borrado el topic de Fase 1. Instalador:
  `instalar_norma_implementacion.py`.

**Doble prueba en vivo (19-ago-2026):**
- Vigente, por chat: Booster corrió la herramienta y encontró un vacío
  real del tenant que nadie sabía — **194 de 198 productos sin código
  UNSPSC** (exigencia SUNAT), 7 sin impuesto, 3 de 6 clientes sin
  documento. Números cruzados contra RPC directo: exactos. Presentó el
  resultado en lenguaje de negocio, hizo la pregunta "a conversar"
  (saldos iniciales) en vez de asumirla, y balanceó con los 15 checks OK
  — tal como le instruye el topic. (Corrió sobre Gemini: OpenAI estaba
  caído esa mañana — la contingencia de proveedor sirvió en un caso real,
  no simulado.)
- Vencida: la guarda cortó con "Servicio suspendido" sin evaluar nada.

**Bug real encontrado en la prueba:** `getattr` no existe en el sandbox
de Odoo (NameError en vivo). Corregido con `'campo' in rec._fields` +
acceso directo, agregado a `BUILTINS_NO_DISPONIBLES` en `guarda_llave.py`,
y ahora hay un test (`test_sin_builtins_no_disponibles`) en las dos
suites (catálogo y Booster) que lo hace cumplir — antes la lista existía
pero nada la verificaba. Las 58 herramientas del catálogo pasan.

## Fuentes del agente Booster (21-ago-2026)

Detectado en el inventario de Fase 1 (21-ago-2026): el agente Booster
tiene `restrict_to_sources=True` desde su creacion pero `sources_ids=[]`
-- cero documentos cargados. El spec (`01-booster-implementador.md`)
pide "guias de implementacion Efficax, instructivos Pack 360, plantillas
RF-10" como fuentes. Se buscaron los tres en el repo cross-repo de
Efficax: **Pack 360 y las plantillas RF-10 no existen como archivos** --
el spec los menciona pero nunca se escribieron. No se inventa su
contenido (misma convencion del catalogo: no fabricar).

**`booster/fuentes/` es LA ruta canonica (21-ago-2026, pedido de
Alberto)** -- donde deben vivir los documentos que Booster consume como
fuente, movidos ahi desde la raiz de `booster/` con `git mv` (conserva
historial). `instalar_fuentes_booster.py` escanea esa carpeta con glob
(`*.md`), no una lista fija en codigo: agregar un documento nuevo (ej.
cuando lleguen Pack 360 o las plantillas RF-10) es soltar el archivo ahi
y volver a correr el instalador -- no hace falta tocar codigo.

**Primera version honesta, instalada:** solo los DOS documentos reales y
ya verificados de este repo, subidos como `ai.agent.source` tipo
`binary` (con `ir.attachment` real, no texto pegado ni URL):

- `fuentes/NORMA-IMPLEMENTACION.md`
- `fuentes/UX-ONBOARDING.md`

Ambos quedaron `status='indexed'` y `sources_fully_processed=True` en el
agente. Instalador idempotente por archivo: si la fuente ya existe para
ese nombre, reemplaza el adjunto en vez de duplicar. Reinstalado desde
la ruta nueva y reverificado en vivo (21-ago-2026): mismos `source_id`
(5, 6), sigue `indexed`.

**Pendiente:** Pack 360 y plantillas RF-10 -- requieren que Alberto los
provea o confirme que se redacten desde cero.

**Prueba en vivo (21-ago-2026):** se le pregunto a Booster algo que solo
podia responder si de verdad leyo los documentos (no algo ya cubierto
por su `system_prompt`): en que fase se instala `x_booster_licencia` y
que verifica el smoke test. Respondio citando la fuente (`[1]`) con el
contenido EXACTO de `fuentes/UX-ONBOARDING.md` -- Fase 3 (Provisioning), los 4
checks del smoke test (Live Chat responde, correo transaccional sale,
metodo de pago carga, llave renovada hoy) y el reporte verde/rojo al
Supervisor. Confirmado texto por texto via RPC, no solo por pantalla.

## Mapa dolores→agentes + autorizados en Fase 1 (21-ago-2026)

Alberto preguntó "qué le falta a Booster" y señaló dos vacíos concretos
de Fase 1, subsanados los dos:

- **`x_agentes_sugeridos`** (campo nuevo, se reemplaza entero en cada
  llamada): Fase 1 recolecta los 3 dolores del dueño pero no producía
  ninguna salida con ellos — el carrito sugerido que debía alimentar la
  Fase 2 se perdía. Se agregó `MAPA_DOLORES_AGENTES` al topic (7 dolores
  reales → código de agente, contra el catálogo real de
  `01`-`10-inventarios.md` — Mentor y Ventas & Atención 24/7 son Básico,
  siempre incluidos; Soporte Postventa es interno, nunca se sugiere a un
  cliente) y el parámetro `agentes_sugeridos` en `guardar_avance_wizard`.
- **`x_autorizados`** (campo nuevo, se acumula como `pendientes` — una
  persona por llamada): Booster ya sabía por el `system_prompt` que
  podía hablar con quien el dueño autorizara, pero no había dónde
  anotarlo. Se agregó la pregunta en el mismo punto que "usuarios y
  roles" de Fase 1, y el parámetro `autorizado`.

**Doble prueba en vivo (21-ago-2026):** un mensaje único con toda la
info de Fase 1 (datos del negocio, camino A, una persona autorizada,
3 dolores reales) verificado exacto via RPC contra
`x_booster_implementacion`: `x_camino='A'`,
`x_agentes_sugeridos='ventas, finanzas, inventarios'` (los 3 dolores
mapearon exactamente a lo diseñado: "no respondo a tiempo"→ventas,
"no sé si alcanza la caja"→finanzas, "mi stock nunca cuadra"→inventarios),
`x_autorizados='Carlos Mendoza, carlos@efficaxba.com'`. No se repitió el
kill-switch: el `GUARDA_TEMPLATE` no se tocó, ya está probado en este
mismo tool.

**Hallazgo real, no relacionado con el código (21-ago-2026):** un canal
`ai_chat` puede quedar **trabado indefinidamente** sin responder a nada
—ni siquiera "hola, estás ahí?"— y el problema sobrevive a un cambio de
proveedor LLM (pasó con GPT-5 y siguió pasando con Gemini en el mismo
canal), así que no es la contingencia de proveedor lo que lo resuelve.
Pasó tras un mensaje duplicado por una desconexión de la extensión de
Chrome a mitad de un envío. Se resolvió eliminando el canal
(`discuss.channel.unlink`) y abriendo uno nuevo — Odoo lo recrea solo al
volver a abrir el chat del agente. Vale la pena tenerlo presente para
Fase 5 (Residencia): si un cliente reporta que su copiloto "dejó de
responder", antes de asumir una caída de proveedor, revisar si el canal
quedó trabado y basta con recrearlo.

## Inventario y kill-switch capa 2 (19-ago-2026)

Prerrequisito de la Fase 3 y del modelo de cobro. El spec exige que cada
cosa que Booster crea quede registrada con etiqueta "creado por Booster"
o "preexistente" -- sin eso, apagar a un cliente que deja de pagar es a
ciegas. Construido y probado en vivo:

- **Modelo `x_booster_inventario`**: una fila por registro (modelo, id,
  nombre, etiqueta, receta de origen, fecha, estado, archivable).
  `perm_unlink=False`: el inventario es auditoría, no se borra.
- **`booster: registrar_en_inventario`** (id 1575): idempotente por
  (modelo, res_id) -- reintentos de recetas no duplican. Calcula
  `x_archivable` leyendo si el modelo tiene `active`. Rechaza ids
  fantasma.
- **`booster: killswitch_inventario`** (id 1576): `listar` (seguro) /
  `apagar` / `reactivar`. Apaga SOLO lo `creado_por_booster`, filtrado
  por etiqueta ANTES de cualquier write; lo `preexistente` ni se carga.
  `apagar`/`reactivar` exigen `confirmar=true` explícito. Lo no
  archivable se salta y se reporta, no se finge.
- Topic "Booster — Inventario y kill-switch" (id 19), enlazado con
  `(4, id)`. Instalador: `instalar_inventario.py`.

**Prueba en vivo (19-ago-2026) -- la invariante central del modelo:**
Mentor piloto inventariado como creado_por_booster, Hasky como
preexistente. `apagar` sin confirmar → no hizo nada. `apagar` confirmado
→ Mentor `active=False`, **Hasky intacto**. `listar` → estados
correctos. `reactivar` → Mentor vuelve, Hasky intacto. Licencia vencida
→ ni con `confirmar=true` ejecuta. Verificado todo por RPC directo sobre
`ai.agent.active`, no por el mensaje. **"Lo nuestro se apagó; lo suyo
jamás"** -- probado.

**Dos hallazgos de harness que importan para futuras pruebas:** (1) un
`raise UserError` al final de una Server Action hace ROLLBACK de toda
la transacción -- el truco de "lanzar el resultado por excepción" que
usé en `evaluar_implementacion` (solo lectura) NO sirve para herramientas
que escriben; usar `log()` → `ir.logging`, que sobrevive al commit.
(2) `ai_tool` con `use_in_ai` recibe params como Python: al inyectarlos
a mano en una prueba hay que usar `repr()`, no `json.dumps()` (`false`
no es Python).

**Pendiente que esto habilita:** las recetas de Fase 3 deben llamar a
`registrar_en_inventario` después de cada `create`; Fase 1-bis (camino
C) debe registrar lo detectado como `preexistente`. Hoy el inventario
tiene 2 filas reales: Mentor piloto (creado) y Hasky (preexistente).

## Ícono de la app (16-ago-2026, iterado tres veces)

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

**Intento 3 (descartado, pero por decisión, no por fallo de ejecución):**
letra "B" geométrica real, tipografía Montserrat Black, naranja sobre
negro. Se leía bien como "B" — reemplazado igual porque Alberto proveyó
un ícono propio real (ver versión actual).

**Versión actual (17-ago-2026):** el mismo sistema modular de
barras/puntos del logo de Efficax, pero esta vez un archivo SVG real
provisto por Alberto (`efficax_letter_b_dynamic_speed.svg`, guardado en
`booster/assets/` como referencia/provenance) — no una reconstrucción a
ojo como los intentos 1 y 2. Reconstruido con Pillow como tile de app
(fondo oscuro `#0D0D0D`, glifo naranja `#FF5500` con resplandor suave) y
un **borde naranja `#FF6A00`** alrededor del tile — pedido explícito de
Alberto para que Booster se distinga a simple vista de Efficax en la
pantalla de un celular, donde ambos van a convivir. Las coordenadas del
glifo (paths/rects/circles) son una copia exacta del SVG, no
reinterpretadas a mano — no se pudo rasterizar el SVG directamente
porque este entorno no tiene la librería nativa `libcairo` que
`cairosvg` necesita, así que se reconstruyó el mismo dibujo con
primitivas de Pillow (curvas Bézier muestreadas a mano para los trazos
gruesos redondeados).

Fuente: `booster/assets/generar_icono.py` (genera
`booster/assets/icono_booster_b.png` desde cero, reproducible — no
editado a mano en un editor de imágenes) + `booster/assets/efficax_letter_b_dynamic_speed.svg`
(el SVG original, guardado como referencia). Instalado vía
`web_icon_data` en `ir.ui.menu` (campo binario para ícono custom, no el
`web_icon` de texto que solo acepta el formato `fa-icono,#fondo,#icono`).
**Detalle no documentado por Odoo, verificado en vivo:** si
`web_icon_data` y `web_icon` se escriben en la misma llamada `write()`,
Odoo vacía `web_icon_data` — hay que escribirlos en llamadas separadas
(así quedó en `instalar_booster_fase1.py`).

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

**Cómo llega el cliente hasta ahí — diseño propuesto (17-ago-2026):**
ver `booster/fuentes/UX-ONBOARDING.md`. Detectado como vacío real (Alberto vio la
lista técnica de `x_booster_implementacion` en el backend de Odoo y
preguntó cómo interactúa un cliente de verdad) — la interfaz real nunca
es esa vista de Odoo, es 100% el chat de Booster. Propuesta: reusar el
trial nativo de Odoo (`saas_trial`, ya instalado, mismo mecanismo que
creó este tenant) como punto de entrada de Fase 1, para no construir
infraestructura de provisioning propia solo para "cómo empieza el
prospecto". Es un diseño, no código — pendiente de que Alberto lo
confirme o ajuste antes de construir Fase 3.

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
