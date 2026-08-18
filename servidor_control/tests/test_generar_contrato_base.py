"""Tests de las invariantes: nunca se sirve una plantilla de una
jurisdiccion sin validar, y nunca se fabrica el cuerpo de un contrato
que no esta en la Biblioteca real (hoy vacia)."""
from app.legal_contratos.generar_contrato_base import (
    BIBLIOTECA_PLANTILLAS,
    DISCLAIMER,
    ParteContrato,
    SolicitudContrato,
    validar_solicitud,
)

PARTES_OK = (
    ParteContrato(nombre="Efficax Solutions SA", rol="arrendador"),
    ParteContrato(nombre="Juan Perez", rol="arrendatario"),
)


def test_tipo_invalido_se_rechaza():
    s = SolicitudContrato(tenant_id=1, tipo="invento", pais="Peru", region="Lima", partes=PARTES_OK)
    r = validar_solicitud(s)
    assert r.valido is False
    assert "tipo invalido" in r.motivo


def test_pais_sin_clausula_validada_se_rechaza():
    s = SolicitudContrato(tenant_id=1, tipo="alquiler", pais="Marte", region="Colonia1", partes=PARTES_OK)
    r = validar_solicitud(s)
    assert r.valido is False
    assert "jurisdiccion" in r.motivo


def test_menos_de_dos_partes_se_rechaza():
    s = SolicitudContrato(tenant_id=1, tipo="alquiler", pais="Peru", region="Lima", partes=(PARTES_OK[0],))
    r = validar_solicitud(s)
    assert r.valido is False
    assert "2 partes" in r.motivo


def test_parte_sin_rol_se_rechaza():
    partes = (ParteContrato(nombre="Juan", rol=""), ParteContrato(nombre="Ana", rol="arrendador"))
    s = SolicitudContrato(tenant_id=1, tipo="alquiler", pais="Peru", region="Lima", partes=partes)
    r = validar_solicitud(s)
    assert r.valido is False
    assert "rol" in r.motivo


def test_peru_valida_pero_sin_plantilla_cargada_se_rechaza():
    # La biblioteca real esta vacia hasta que Alberto la provea -- ver docstring.
    assert ("alquiler", "Peru") not in BIBLIOTECA_PLANTILLAS
    s = SolicitudContrato(tenant_id=1, tipo="alquiler", pais="Peru", region="Lima", partes=PARTES_OK)
    r = validar_solicitud(s)
    assert r.valido is False
    assert "Biblioteca" in r.motivo
    assert r.clausula_jurisdiccion is not None


def test_disclaimer_siempre_presente():
    s = SolicitudContrato(tenant_id=1, tipo="alquiler", pais="Peru", region="Lima", partes=PARTES_OK)
    r = validar_solicitud(s)
    assert r.disclaimer == DISCLAIMER
    assert "PLANTILLA" in r.disclaimer
    assert "abogado" in r.disclaimer
