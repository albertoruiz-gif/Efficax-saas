# Norma de Implementación Odoo — Efficax Booster

**Base:** "Implementación del Sistema Odoo — Localización Perú" v1.0
(consultora Constanza Herrera, 30/04/2025), aportado por Alberto el
19-ago-2026 con la instrucción de complementarlo y adoptarlo como norma
de Booster.

**Marcas de origen — para saber qué es del manual y qué se complementó:**
- `[M]` — viene del manual original (a veces reordenado, nunca inventado).
- `[+]` — complemento de Efficax (vacío del manual, cubierto con lo
  verificado en vivo en el tenant o con criterio explícito de Alberto).

**Cómo la usa Booster (doble función, pedida por Alberto):**
1. **Como procedimiento**: al implementar un cliente nuevo, las fases se
   ejecutan en este orden — cada una tiene prerequisitos de la anterior.
2. **Como evaluador de vacíos**: sobre un Odoo ya andando (camino
   Fase 1-bis: "ya tiene Odoo"), la herramienta `evaluar_implementacion`
   corre los checks automáticos (marcados `✓auto`) y reporta qué falta,
   priorizado. Los ítems sin `✓auto` se evalúan conversando con el dueño.

---

## FASE 0 — Fundaciones (nada funciona bien si esto está mal)

| # | Ítem | Origen | Verificación |
|---|------|--------|--------------|
| 0.1 | Acceso admin, internet estable, país Perú seleccionado | [M] | manual |
| 0.2 | País de la compañía = Perú, moneda = PEN | [M] | ✓auto |
| 0.3 | Localización instalada: `l10n_pe` (plan contable PCGE), `l10n_pe_edi` (facturación electrónica), `l10n_pe_reports` (PLE), `l10n_pe_edi_stock` (guía de remisión) | [M] | ✓auto |
| 0.4 | Con la localización deben existir: impuestos, plan contable, posiciones fiscales (local/exportación), tipos de identificación (RUC, DNI, ...), tipos de documento SUNAT | [M] | ✓auto |
| 0.5 | Datos de compañía completos: RUC, código de establecimiento (0000 si se desconoce), dirección con departamento/provincia/distrito, ubigeo | [M] | ✓auto (RUC/dirección) |
| 0.6 | Proveedor de firma digital (OSE) elegido y configurado: IAP, Digiflow o SUNAT, con credenciales/certificados | [M] | ✓auto (elegido) |
| 0.7 | Usuarios y permisos: grupos Administrador, Vendedor, Contador, CRM; roles por módulo | [M] | ✓auto (conteo) |
| 0.8 | **Principio de mínimo acceso y accesos-de-una-sola-vez**: todos los accesos que la implementación necesitará (API key técnica, OSE, pagos, DNS, píxeles) se levantan en UN solo checkpoint, no de a poco. API keys con renovación gestionada, no manual | [+] regla ya establecida en `booster/README.md` (17-ago-2026) | manual |
| 0.9 | Diarios contables: ventas, compras, pagos, banco, efectivo — cada uno con tipo de documento y secuencia SUNAT única y correlativa | [M] | ✓auto |
| 0.10 | Plan de cuentas basado en PCGE, cuentas mapeadas a impuestos y diarios | [M] | ✓auto (existencia) |

## FASE 1 — Datos maestros (antes de operar, el sistema tiene que saber qué vendes y a quién)

| # | Ítem | Origen | Verificación |
|---|------|--------|--------------|
| 1.1 | Productos: código UNSPSC (exigencia SUNAT), tipo correcto (almacenable/consumible/servicio), impuesto de venta asignado | [M] | ✓auto (faltantes) |
| 1.2 | Clientes: tipo de documento (RUC/DNI/...), número, dirección con ubigeo | [M] | ✓auto (faltantes) |
| 1.3 | Proveedores: RUC en campo NIF formato SUNAT, condiciones de pago y plazos de entrega | [M] | ✓auto (faltantes) |
| 1.4 | Listas de precios de proveedor por producto (múltiples proveedores, descuentos por volumen) | [M] | manual |
| 1.5 | **Migración de datos iniciales** — el manual no la cubre y es el vacío más grande: contactos históricos, saldos contables iniciales, deudas por cobrar/pagar abiertas, y stock inicial. Nota verificada en el tenant: la carga inicial de stock pasa por la ubicación "Inventory adjustment" — los reportes de ajustes deben excluir esa carga inicial o mienten | [+] | manual |
| 1.6 | Condiciones de pago definidas (contado, crédito 15/30/60, detracciones si aplica) | [M] | ✓auto (existencia) |

## FASE 2 — Flujos operativos por módulo

### 2A. Ventas [M]
1. Tipos de documento de venta SUNAT verificados (Factura 01, Boleta, NC, ND) con su código.
2. Secuencias por diario correlativas.
3. Impuestos: IGV 18%, exonerado, inafecto — con código SUNAT.
4. Flujo completo probado: cotización → confirmación → entrega validada → factura → envío a SUNAT vía OSE → zip con XML+CDR descargado → y la reversa: nota de crédito (factura rectificativa) enviada y validada. `✓auto` (existencia de flujo configurado; la prueba es de Fase 3).

### 2B. CRM [M]
1. Etapas del pipeline definidas según el flujo real de la empresa (no las de fábrica).
2. Oportunidades con vendedor asignado y fechas de seguimiento.
3. Actividades programadas (llamada/reunión/correo) con recordatorios.
4. Análisis de pipeline: tasa de conversión, valor promedio, duración de ciclo.

### 2C. Compras [M]
1. Carga de facturas de proveedor desde XML (el archivo que empieza con el RUC; múltiple si hace falta).
2. Productos comprables con precios por proveedor.
3. Reglas de reabastecimiento (mín/máx) para generar órdenes automáticas.
4. Flujos de aprobación de órdenes de compra si el cliente los necesita.

### 2D. Inventario [M solo guía de remisión — complementado]
1. Guía de remisión electrónica configurada (Inventario > Ajustes) [M].
2. Plazo de seguridad de compra configurado [M].
3. `[+]` Almacenes y ubicaciones según la realidad física del negocio.
4. `[+]` Valoración de inventario definida (estándar/promedio/FIFO) ANTES de cargar stock.
5. `[+]` Conteos cíclicos y clasificación ABC (Booster ya trae las 7 herramientas del agente de inventarios probadas en vivo — usarlas es parte de la implementación, no un extra).

### 2E. Contabilidad y cobranzas [M]
1. Facturación electrónica emitiendo y validando contra SUNAT.
2. Reportes PLE generables en .txt: RVIE, RCE, Libro Diario, Mayor, Caja y Bancos.
3. Cuentas bancarias creadas ordenadamente en el plan; diario bancario con cuentas de pagos/cobros pendientes entendidas (o pago directo a banco si el cliente no concilia contra extracto).
4. Conciliación: registro de extracto → emparejamiento sugerido → validar.
5. Límite de crédito por cliente habilitado, con límite por defecto y personalización por cliente.
6. Detracciones: condición de pago + producto de detracción con su porcentaje, diarios en soles y dólares.
7. **Niveles de seguimiento de cobranza con las reglas legales del manual (INDECOPI)** — esto es norma, no sugerencia: transparencia (motivo, monto, opciones de pago en toda comunicación), no acoso (máx. 1 contacto/día), horario 7:00-20:00 lunes a sábado, no comunicar deuda a terceros. Las plantillas de correo de cada nivel deben cumplirlo. `[M]` — y coincide con el playbook de cobranzas ya implementado en las herramientas de finanzas.
8. Activos y depreciación si el cliente los maneja [M apuntes].

## FASE 3 — Verificación y pruebas [+ estructurado; el manual solo dice "pruebas exhaustivas"]

1. **Smoke test de punta a punta con datos de prueba**: una venta completa
   (cotización→SUNAT→NC de reversa), una compra desde XML, una
   conciliación. Igual al smoke test ya definido para el cierre de la
   Fase 3 de Booster en `fuentes/UX-ONBOARDING.md`.
2. **Doble prueba de toda automatización instalada** (recordatorios,
   reabastecimiento, agentes): caso feliz + caso de falla — misma
   convención que las 58 herramientas del catálogo.
3. Pruebas con datos reales del cliente antes del corte [M].
4. Limpiar TODOS los datos de prueba antes del go-live (documentar cada
   registro de prueba creado — lección de esta sesión: los datos de
   prueba huérfanos bloquean flujos después).

## FASE 4 — Go-live [+; el manual no lo estructura]

1. Respaldo/duplicado de la base antes del corte [M lo menciona al pasar: "duplicar la base de datos"].
2. Verificar que las secuencias reales no arrastren numeración de pruebas.
3. Usuarios finales creados con sus permisos reales (no todos admin).
4. Capacitación del personal clave en Odoo y en los procesos propios [M].
5. Canal de soporte activo y comunicado [M] — para clientes Booster: Mentor + correo soporte@efficaxba.com (respuesta ≤ 2 días hábiles, según contrato).

## FASE 5 — Post-implementación [M ampliado]

1. Soporte y mantenimiento con canal establecido [M].
2. Sistema actualizado con últimas versiones y parches [M].
3. `[+]` Monitoreo de agentes: la contingencia de proveedor LLM
   (OpenAI→Gemini) ya corre cada 2 min en el tenant — verificar que esté
   activa en cada implementación nueva.
4. `[+]` Revisión a los 30 días: correr `evaluar_implementacion` de
   nuevo y comparar contra el corte — los vacíos nuevos son deuda
   operativa del cliente, los viejos son deuda de implementación.

---

## Vacíos conocidos de esta norma (honestidad ante todo)

- **RRHH, Marketing, Sitio Web, Documentos/Firma, Proyectos**: el manual
  no los cubre y esta norma tampoco los inventa. Booster los implementa
  vía el catálogo de agentes (probados en vivo), pero la configuración
  base de esos módulos queda pendiente de documentar cuando se
  implemente el primer cliente real que los use.
- **Otras localizaciones**: esta norma es Perú (SUNAT/PCGE/INDECOPI).
  Para otro país aplica el mismo criterio que las cláusulas de
  jurisdicción del contrato: no se implementa sin validar la
  localización local — no se improvisa.
- Los apuntes sueltos del documento original (guía de certificación
  Odoo 18, notas de Studio, alquileres) NO son parte de la norma — son
  material de estudio de la consultora y quedan en el documento fuente.
