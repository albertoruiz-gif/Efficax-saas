"""Configuración fail-closed del Servidor de Control.

Regla (lección Haskell, auditoría 2026-08-10): ningún secreto tiene valor por
defecto. Si falta la variable, la aplicación NO arranca — jamás corre firmando
con un secreto público conocido.
"""
from __future__ import annotations

import os


class ConfigError(RuntimeError):
    """Falta configuración obligatoria — la app no debe arrancar."""


def secreto(nombre: str) -> str:
    """Lee un secreto de entorno. Fail-closed: sin default, sin cadena vacía."""
    valor = os.environ.get(nombre, "").strip()
    if not valor:
        raise ConfigError(
            f"Variable de entorno obligatoria ausente: {nombre}. "
            "El Servidor de Control no arranca sin ella (fail-closed)."
        )
    return valor


def es_ci() -> bool:
    return os.environ.get("EFX_ENV") == "ci"
