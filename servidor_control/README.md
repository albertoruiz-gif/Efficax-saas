# Servidor de Control

El servicio (AWS de Efficax, según el RFD) que hace las veces de "cerebro"
fuera del tenant de cada cliente: ciclo de renovación de llaves, y las
recetas de herramientas marcadas `ejecuta: "servidor_control"` en el
catálogo (`herramientas_esquemas.json`) — esas NO se instalan como
`ir.actions.server` dentro del Odoo del cliente, corren acá.

**Estado real (16-ago-2026): API de solo `/health`, nada más desplegado.**
Hasta que haya volumen de clientes, Alberto hace las veces de este
servicio manualmente (RPC directo, como toda herramienta probada esta
noche) — así quedó acordado explícitamente. Lo que sigue documenta qué
hay construido hoy y qué falta para que sea un servicio real invocable
por los agentes.

## Patrón: lógica pura primero, red aparte

Cada pieza sigue el mismo patrón que `app/llaves/renovacion.py` (el
primero, ya con esta convención): la DECISIÓN es una función pura, sin
I/O, 100% testeable sin mocks ni red. La escritura real (XML-RPC hacia el
Odoo del tenant, o hacia Casa Efficax) es un paso aparte, deliberadamente
no mezclado con la decisión — para que la regla de negocio se pueda
probar sin depender de que un Odoo esté arriba.

- `app/llaves/renovacion.py` — decide si renovar la llave de un tenant
  (invariante: nunca se renueva la de un moroso). Escritura real: **no
  implementada**.
- `app/mentor/acceso.py` — `actualizar_perfil_acceso`: valida que quien
  autoriza sea el dueño registrado (`aprobacion: "dueno"`, más estricto
  que "confirmar") y resuelve qué grupos de Odoo corresponden al perfil
  pedido, según el mapeo de Fase 3 de ESE tenant (nunca hardcodeado — si
  el perfil no está en el mapeo, se rechaza explícito). Escritura real
  (XML-RPC a `res.users`/`res.groups` del tenant): **no implementada**.
- `app/mentor/escalamiento.py` — `abrir_ticket_efficax`: valida y arma el
  payload de un ticket hacia el Helpdesk de Casa Efficax (la instancia
  propia de Efficax, no el tenant del cliente). Envío real (XML-RPC hacia
  Casa Efficax): **no implementada**.

## Qué falta para que esto sea invocable de verdad

1. **Registro de tenants** (`app/tenants/`, hoy vacío): credenciales de
   RPC por tenant, para que el Servidor de Control sepa a qué base
   conectarse. Sin esto, la escritura real no tiene a dónde escribir.
2. **Endpoints FastAPI** en `app/main.py` (hoy solo `/health`) que
   reciban la solicitud, llamen a la función de decisión pura, y si es
   válida, ejecuten la escritura real vía XML-RPC.
3. **Autenticación del llamador**: hoy nada protege estos endpoints —
   necesitan verificar que quien llama es realmente el tenant que dice
   ser (ver RF-22, "usuario técnico + API key + company_id explícito,
   fail-closed").
4. **Despliegue en algún lugar alcanzable desde el Odoo del cliente**
   (Odoo Online no tiene acceso a `localhost`) — no hay decisión tomada
   todavía sobre dónde (AWS según el RFD, pero no aprovisionado).
5. **El lado Odoo**: un `ir.actions.server` que haga la llamada HTTP de
   salida hacia acá — no probado si `requests`/`urllib` está disponible
   en el sandbox de IA (mismo sandbox que bloqueó `type()` y las clases
   de excepción nombradas, ver `server_actions/implementaciones/README.md`).

Cuando exista volumen de clientes real y se aborde esto, el orden lógico
es 1→2→3→5→4 (probar localmente end-to-end antes de pensar en dónde
desplegar).
