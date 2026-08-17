"""Tests de la invariante: aprobacion='dueno' -- solo el dueno registrado
del tenant puede autorizar cambios de acceso, y el perfil pedido tiene que
existir en el mapeo de Fase 3 de ese tenant (nunca se inventa un grupo)."""
from app.mentor.acceso import SolicitudCambioAcceso, validar_solicitud

MAPEO_EJEMPLO = {
    "gerente_general": ("group_erp_manager", "group_hr_manager"),
    "administrativo": ("group_account_invoice",),
}


def test_solo_el_dueno_puede_autorizar():
    s = SolicitudCambioAcceso(
        tenant_id=1, usuario="ana", accion="alta",
        solicitante_es_dueno=False, perfil_nuevo="gerente_general",
    )
    r = validar_solicitud(s, MAPEO_EJEMPLO)
    assert r.valido is False
    assert "dueno" in r.motivo


def test_alta_con_perfil_valido_asigna_sus_grupos():
    s = SolicitudCambioAcceso(
        tenant_id=1, usuario="ana", accion="alta",
        solicitante_es_dueno=True, perfil_nuevo="gerente_general",
    )
    r = validar_solicitud(s, MAPEO_EJEMPLO)
    assert r.valido is True
    assert r.grupos_a_asignar == ("group_erp_manager", "group_hr_manager")


def test_perfil_no_definido_en_el_tenant_se_rechaza():
    s = SolicitudCambioAcceso(
        tenant_id=1, usuario="ana", accion="cambio_perfil",
        solicitante_es_dueno=True, perfil_nuevo="perfil_inventado",
    )
    r = validar_solicitud(s, MAPEO_EJEMPLO)
    assert r.valido is False
    assert "no esta definido" in r.motivo


def test_cambio_perfil_sin_perfil_nuevo_se_rechaza():
    s = SolicitudCambioAcceso(
        tenant_id=1, usuario="ana", accion="cambio_perfil",
        solicitante_es_dueno=True, perfil_nuevo=None,
    )
    r = validar_solicitud(s, MAPEO_EJEMPLO)
    assert r.valido is False
    assert "perfil_nuevo" in r.motivo


def test_baja_no_necesita_perfil_nuevo_y_vacia_los_grupos():
    s = SolicitudCambioAcceso(
        tenant_id=1, usuario="ana", accion="baja",
        solicitante_es_dueno=True,
    )
    r = validar_solicitud(s, MAPEO_EJEMPLO)
    assert r.valido is True
    assert r.grupos_a_asignar == ()


def test_accion_invalida_se_rechaza():
    s = SolicitudCambioAcceso(
        tenant_id=1, usuario="ana", accion="ascenso_magico",
        solicitante_es_dueno=True,
    )
    r = validar_solicitud(s, MAPEO_EJEMPLO)
    assert r.valido is False


def test_falta_usuario_se_rechaza():
    s = SolicitudCambioAcceso(
        tenant_id=1, usuario="  ", accion="baja",
        solicitante_es_dueno=True,
    )
    r = validar_solicitud(s, MAPEO_EJEMPLO)
    assert r.valido is False
    assert "usuario" in r.motivo
