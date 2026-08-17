"""Tests de la invariante: aprobacion='dueno' -- solo el dueno registrado
del tenant puede autorizar una publicacion publica, y no se publica nada
si el tenant no tiene LinkedIn conectado (eso es de Fase 3, no de esta
herramienta)."""
from app.rrhh.publicar_linkedin import SolicitudPublicacion, validar_solicitud


def test_solo_el_dueno_puede_autorizar():
    s = SolicitudPublicacion(
        tenant_id=1, puesto_id=10, texto_publicacion="Buscamos...",
        solicitante_es_dueno=False, linkedin_conectado=True,
    )
    r = validar_solicitud(s)
    assert r.valido is False
    assert "dueno" in r.motivo


def test_sin_linkedin_conectado_se_rechaza():
    s = SolicitudPublicacion(
        tenant_id=1, puesto_id=10, texto_publicacion="Buscamos...",
        solicitante_es_dueno=True, linkedin_conectado=False,
    )
    r = validar_solicitud(s)
    assert r.valido is False
    assert "conectada" in r.motivo


def test_solicitud_completa_y_valida():
    s = SolicitudPublicacion(
        tenant_id=1, puesto_id=10, texto_publicacion="Buscamos un contador...",
        solicitante_es_dueno=True, linkedin_conectado=True,
    )
    r = validar_solicitud(s)
    assert r.valido is True


def test_falta_puesto_id_se_rechaza():
    s = SolicitudPublicacion(
        tenant_id=1, puesto_id=0, texto_publicacion="Buscamos...",
        solicitante_es_dueno=True, linkedin_conectado=True,
    )
    r = validar_solicitud(s)
    assert r.valido is False
    assert "puesto_id" in r.motivo


def test_texto_vacio_se_rechaza():
    s = SolicitudPublicacion(
        tenant_id=1, puesto_id=10, texto_publicacion="   ",
        solicitante_es_dueno=True, linkedin_conectado=True,
    )
    r = validar_solicitud(s)
    assert r.valido is False
    assert "texto_publicacion" in r.motivo


def test_texto_demasiado_largo_se_rechaza():
    s = SolicitudPublicacion(
        tenant_id=1, puesto_id=10, texto_publicacion="x" * 3001,
        solicitante_es_dueno=True, linkedin_conectado=True,
    )
    r = validar_solicitud(s)
    assert r.valido is False
    assert "3000" in r.motivo
