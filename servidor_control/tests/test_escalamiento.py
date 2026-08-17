"""Tests de armado del ticket hacia el Helpdesk de Casa Efficax."""
from app.mentor.escalamiento import SolicitudEscalamiento, construir_ticket


def test_ticket_valido_arma_payload_con_tenant_identificado():
    s = SolicitudEscalamiento(
        tenant_id=7, tenant_nombre="AutoParts Lima",
        asunto="No sincroniza WhatsApp", descripcion="Desde ayer no llegan mensajes.",
        severidad="alta",
    )
    r = construir_ticket(s)
    assert r.valido is True
    assert r.payload_ticket["name"] == "[AutoParts Lima] No sincroniza WhatsApp"
    assert "AutoParts Lima" in r.payload_ticket["description"]
    assert r.payload_ticket["priority"] == "2"


def test_severidad_invalida_se_rechaza():
    s = SolicitudEscalamiento(
        tenant_id=7, tenant_nombre="AutoParts Lima",
        asunto="x", descripcion="y", severidad="urgentisima",
    )
    r = construir_ticket(s)
    assert r.valido is False


def test_falta_asunto_se_rechaza():
    s = SolicitudEscalamiento(
        tenant_id=7, tenant_nombre="AutoParts Lima",
        asunto="  ", descripcion="y", severidad="baja",
    )
    r = construir_ticket(s)
    assert r.valido is False
    assert "asunto" in r.motivo


def test_falta_descripcion_se_rechaza():
    s = SolicitudEscalamiento(
        tenant_id=7, tenant_nombre="AutoParts Lima",
        asunto="x", descripcion=" ", severidad="baja",
    )
    r = construir_ticket(s)
    assert r.valido is False
    assert "descripcion" in r.motivo
