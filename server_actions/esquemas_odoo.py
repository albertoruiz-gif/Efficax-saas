"""Saneador de JSON Schema para el campo `ai_tool_schema` de Odoo 19.

## Por qué existe

Odoo NO acepta JSON Schema completo en `ir.actions.server.ai_tool_schema`:
valida el esquema al guardar y rechaza la mayoría de las palabras clave.
El catálogo `herramientas_esquemas.json` sí usa JSON Schema completo (es la
spec de negocio, y debe seguir siéndolo). Este módulo traduce de uno al otro.

## Qué acepta Odoo (probado empíricamente en el tenant de Efficax, 15-ago-2026)

Aceptado:
  - nivel raíz: `type: "object"`, `properties`, `required` (OBLIGATORIO —
    omitirlo hace fallar la validación, aunque sea una lista vacía)
  - por propiedad: `type` (string/number/integer/boolean/array),
    `description`, `enum`, `pattern`
  - `array` cuyo `items` sea de tipo ESCALAR

Rechazado (cada uno verificado uno por uno):
  - `default`, `minLength`, `maxLength`, `format`, `minimum`, `maximum`,
    `exclusiveMinimum`, `minItems`, `maxItems`
  - objetos anidados (una propiedad de tipo `object` con `properties`)
  - arrays de objetos
  - `$ref` / `$defs`, `anyOf` / `oneOf` / `allOf`, `if` / `then`

## Cómo se traduce lo que Odoo no soporta

  - `$ref` -> se resuelve contra `$defs` y se sanea el resultado.
  - objeto anidado -> se APLANA en escalares `padre_hijo`
    (ej. `periodo` {desde, hasta} -> `periodo_desde`, `periodo_hasta`).
  - array de objetos -> se convierte en UN parámetro string `<nombre>_json`,
    cuya descripción explica la estructura exacta que debe traer. La Server
    Action lo parsea con `json.loads`. Es feo, pero es honesto: el LLM
    escribe JSON perfectamente, y la alternativa (perder el parámetro) sería
    peor.
  - palabras clave de validación no soportadas -> se ELIMINAN del esquema y
    se trasladan al texto de `description`, para que el modelo siga viendo
    la restricción aunque Odoo ya no la haga cumplir. La validación real es
    responsabilidad del cuerpo de la Server Action, no del esquema.
"""
from __future__ import annotations

from typing import Any

TIPOS_ESCALARES = {"string", "number", "integer", "boolean"}

# Palabras clave que Odoo rechaza pero que sí llevan información útil para el
# modelo: en vez de perderlas, se anexan a la descripción en lenguaje natural.
RESTRICCIONES_A_TEXTO = {
    "default": "por defecto {}",
    "minLength": "mínimo {} caracteres",
    "maxLength": "máximo {} caracteres",
    "minimum": "mínimo {}",
    "maximum": "máximo {}",
    "exclusiveMinimum": "mayor que {}",
    "minItems": "al menos {} elementos",
    "maxItems": "como máximo {} elementos",
    "format": "formato {}",
}

CLAVES_PERMITIDAS_PROPIEDAD = {"type", "description", "enum", "pattern", "items"}


class EsquemaNoTraducible(ValueError):
    """El esquema tiene una construcción que no se puede representar en Odoo."""


def _resolver_ref(nodo: dict, defs: dict) -> dict:
    """Resuelve '#/$defs/periodo' contra el diccionario de definiciones."""
    ref = nodo.get("$ref")
    if not ref:
        return nodo
    if not ref.startswith("#/$defs/"):
        raise EsquemaNoTraducible(f"$ref no soportado: {ref}")
    clave = ref.split("/")[-1]
    if clave not in defs:
        raise EsquemaNoTraducible(f"$ref apunta a una definición inexistente: {ref}")
    resuelto = dict(defs[clave])
    # Un $ref puede venir acompañado de description propia; esa gana.
    for k, v in nodo.items():
        if k != "$ref":
            resuelto[k] = v
    return resuelto


def _descripcion_con_restricciones(nodo: dict) -> str:
    """Junta la description original con las restricciones que Odoo descarta."""
    partes = []
    if nodo.get("description"):
        partes.append(nodo["description"].strip())
    extras = [
        plantilla.format(nodo[clave])
        for clave, plantilla in RESTRICCIONES_A_TEXTO.items()
        if clave in nodo
    ]
    if extras:
        partes.append("(" + "; ".join(extras) + ")")
    return " ".join(partes).strip()


def _sanear_escalar(nodo: dict) -> dict:
    salida: dict[str, Any] = {"type": nodo.get("type", "string")}
    desc = _descripcion_con_restricciones(nodo)
    if desc:
        salida["description"] = desc
    if "enum" in nodo:
        salida["enum"] = nodo["enum"]
    if "pattern" in nodo:
        salida["pattern"] = nodo["pattern"]
    return salida


def _describir_estructura(items: dict, defs: dict) -> str:
    """Texto que explica al modelo qué forma debe tener cada objeto del array."""
    items = _resolver_ref(items, defs)
    props = items.get("properties", {})
    obligatorios = set(items.get("required", []))
    campos = []
    for nombre, sub in props.items():
        sub = _resolver_ref(sub, defs)
        marca = "" if nombre in obligatorios else " (opcional)"
        campos.append(f"{nombre}: {sub.get('type', 'string')}{marca}")
    return "{" + ", ".join(campos) + "}"


def sanear_propiedad(nombre: str, nodo: dict, defs: dict) -> dict[str, dict]:
    """Convierte UNA propiedad del catálogo en 0..N propiedades válidas en Odoo.

    Devuelve un dict porque aplanar un objeto anidado produce varias.
    """
    nodo = _resolver_ref(nodo, defs)
    tipo = nodo.get("type")

    if tipo == "object" and "properties" in nodo:
        # Objeto anidado -> se aplana en escalares padre_hijo.
        salida = {}
        for sub_nombre, sub in nodo["properties"].items():
            sub = _resolver_ref(sub, defs)
            if sub.get("type") == "object" or sub.get("type") == "array":
                raise EsquemaNoTraducible(
                    f"{nombre}.{sub_nombre}: anidamiento de más de un nivel"
                )
            plano = _sanear_escalar(sub)
            contexto = f"Parte '{sub_nombre}' de {nombre}."
            plano["description"] = (
                contexto + " " + plano.get("description", "")
            ).strip()
            salida[f"{nombre}_{sub_nombre}"] = plano
        return salida

    if tipo == "array":
        items = _resolver_ref(nodo.get("items", {"type": "string"}), defs)
        if items.get("type") == "object":
            # Array de objetos -> un solo string con JSON dentro.
            estructura = _describir_estructura(nodo.get("items", {}), defs)
            desc = _descripcion_con_restricciones(nodo)
            return {
                f"{nombre}_json": {
                    "type": "string",
                    "description": (
                        f"{desc} Texto JSON con una lista de objetos "
                        f"{estructura}. Ejemplo: [{estructura}]."
                    ).strip(),
                }
            }
        salida_arr: dict[str, Any] = {
            "type": "array",
            "items": {"type": items.get("type", "string")},
        }
        desc = _descripcion_con_restricciones(nodo)
        if desc:
            salida_arr["description"] = desc
        return {nombre: salida_arr}

    if tipo == "object":
        # Objeto libre (sin `properties` declaradas): en el catálogo se usa
        # para payloads abiertos, ej. `datos` en generar_contrato_base. No hay
        # forma de declararlo en Odoo, así que viaja como texto JSON.
        desc = _descripcion_con_restricciones(nodo)
        return {
            f"{nombre}_json": {
                "type": "string",
                "description": (
                    f"{desc} Texto JSON con un objeto de pares clave-valor."
                ).strip(),
            }
        }

    if tipo in TIPOS_ESCALARES or tipo is None:
        return {nombre: _sanear_escalar(nodo)}

    raise EsquemaNoTraducible(f"{nombre}: tipo no soportado '{tipo}'")


def sanear_para_odoo(input_schema: dict, defs: dict | None = None) -> dict:
    """Traduce un `input_schema` del catálogo a un `ai_tool_schema` de Odoo.

    `required` siempre se emite (aunque vaya vacío): Odoo rechaza el esquema
    si falta. Los nombres renombrados por aplanado/JSON se propagan a la
    lista de obligatorios para no dejar referencias colgando.
    """
    defs = defs or {}
    propiedades: dict[str, dict] = {}
    renombres: dict[str, list[str]] = {}

    for nombre, nodo in (input_schema.get("properties") or {}).items():
        generadas = sanear_propiedad(nombre, nodo, defs)
        propiedades.update(generadas)
        renombres[nombre] = list(generadas.keys())

    obligatorios: list[str] = []
    for nombre in input_schema.get("required", []) or []:
        obligatorios.extend(renombres.get(nombre, [nombre]))

    return {
        "type": "object",
        "properties": propiedades,
        "required": obligatorios,
    }
