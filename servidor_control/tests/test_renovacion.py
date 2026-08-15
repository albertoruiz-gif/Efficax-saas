"""Tests de la invariante: jamás se renueva la llave de un tenant moroso,
y la guarda de 48h se comporta exactamente como la instalada en los tenants."""
from datetime import datetime, timedelta, timezone

from app.llaves.renovacion import (
    Tenant,
    decidir_renovacion,
    llave_vigente,
)


def test_tenant_moroso_nunca_renueva():
    t = Tenant(id=1, nombre="moroso SA", al_dia=False)
    r = decidir_renovacion(t)
    assert r.renovada is False
    assert r.token is None
    assert "moroso" in r.motivo


def test_tenant_al_dia_renueva_con_token_nuevo():
    t = Tenant(id=2, nombre="puntual SAC", al_dia=True)
    r1 = decidir_renovacion(t)
    r2 = decidir_renovacion(t)
    assert r1.renovada and r2.renovada
    assert r1.token and r2.token and r1.token != r2.token  # token no reutilizable


def test_guarda_48h_exacta():
    ahora = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
    dentro = ahora - timedelta(hours=47, minutes=59)
    borde = ahora - timedelta(hours=48)
    fuera = ahora - timedelta(hours=48, minutes=1)
    assert llave_vigente(dentro, ahora) is True
    assert llave_vigente(borde, ahora) is True      # 48h inclusive
    assert llave_vigente(fuera, ahora) is False     # 48h + 1 min = suspendido
