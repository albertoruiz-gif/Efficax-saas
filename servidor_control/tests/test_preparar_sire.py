"""Tests de la invariante: aprobacion='dueno' -- solo el dueno registrado
del tenant puede autorizar preparar un registro tributario, y el periodo
debe tener formato valido antes de generar nada."""
from app.finanzas_tributario.preparar_sire import SolicitudSire, validar_solicitud


def test_solo_el_dueno_puede_autorizar():
    s = SolicitudSire(tenant_id=1, registro="RVIE", periodo="2026-07", solicitante_es_dueno=False)
    r = validar_solicitud(s)
    assert r.valido is False
    assert "dueno" in r.motivo


def test_solicitud_completa_y_valida():
    s = SolicitudSire(tenant_id=1, registro="ambos", periodo="2026-07", solicitante_es_dueno=True)
    r = validar_solicitud(s)
    assert r.valido is True


def test_registro_invalido_se_rechaza():
    s = SolicitudSire(tenant_id=1, registro="RVIX", periodo="2026-07", solicitante_es_dueno=True)
    r = validar_solicitud(s)
    assert r.valido is False
    assert "registro invalido" in r.motivo


def test_periodo_mal_formado_se_rechaza():
    s = SolicitudSire(tenant_id=1, registro="RCE", periodo="07-2026", solicitante_es_dueno=True)
    r = validar_solicitud(s)
    assert r.valido is False
    assert "periodo" in r.motivo


def test_mes_invalido_se_rechaza():
    s = SolicitudSire(tenant_id=1, registro="RCE", periodo="2026-13", solicitante_es_dueno=True)
    r = validar_solicitud(s)
    assert r.valido is False
    assert "periodo" in r.motivo
