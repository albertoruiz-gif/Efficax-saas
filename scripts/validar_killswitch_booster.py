"""
Validación técnica del kill-switch de Booster (tenant #0).

Qué prueba este script, contra una base Odoo de prueba (trial gratuita
o instancia real con un agente de prueba ya creado vía la interfaz):

  1. Conectarse desde AFUERA vía XML-RPC (el mismo patrón que usará
     el Módulo SaaS Efficax en producción) con un usuario de servicio
     dedicado -- NUNCA con tu usuario admin personal. Esto cumple la
     Política de Uso Aceptable de Odoo, que exige "bot users" dedicados
     para integraciones (ver fuente al final).
  2. Leer el estado actual (activo/archivado) de un Agente por nombre.
  3. Archivarlo (simula "no pagó" -> Booster apaga el agente).
  4. Verificar que quedó archivado.
  5. Desarchivarlo (simula "pagó" -> Booster lo reactiva).

Respeta el límite de la Política de Uso Aceptable de Odoo: llamadas
NO paralelas, con pausa entre ellas (nunca ráfagas).

Requisitos antes de correr:
  - pip install --break-system-packages
  - Un usuario de servicio en Odoo (Ajustes > Usuarios) con permisos
    mínimos sobre el modelo de Agentes -- NO admin.
  - El nombre exacto de un Agente de prueba ya creado en esa base
    (ej. duplicar "Hasky" y llamarlo "Agente Prueba Killswitch").

Uso:
  python validar_killswitch_booster.py \
      --url https://TU-INSTANCIA.odoo.com \
      --db NOMBRE_BASE \
      --user usuario_servicio@dominio.com \
      --password "..." \
      --agente "Agente Prueba Killswitch"
"""

import argparse
import sys
import time
import xmlrpc.client

# Nombre técnico real del modelo de Agentes en Odoo 19.
# Se confirma en tiempo de ejecución contra el esquema de la base
# (algunas instalaciones lo exponen como 'ai.agent'; si difiere,
# el script lo reporta claramente en vez de fallar en silencio).
MODELOS_CANDIDATOS = ["ai.agent"]

PAUSA_ENTRE_LLAMADAS_SEG = 1.2  # cumple el límite ~1 req/seg de Odoo


def conectar(url, db, user, password):
    common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
    version = common.version()
    print(f"[OK] Conectado a Odoo. Versión del servidor: {version.get('server_version')}")

    uid = common.authenticate(db, user, password, {})
    if not uid:
        print("[ERROR] Autenticación fallida. Revisa usuario/clave/nombre de base.")
        sys.exit(1)
    print(f"[OK] Autenticado como uid={uid} (usuario de servicio, no admin personal)")

    models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")
    return uid, models


def detectar_modelo(models, db, uid, password):
    for modelo in MODELOS_CANDIDATOS:
        try:
            models.execute_kw(db, uid, password, modelo, "search", [[]], {"limit": 1})
            print(f"[OK] Modelo de Agentes accesible por API externa: '{modelo}'")
            return modelo
        except xmlrpc.client.Fault as e:
            print(f"[INFO] '{modelo}' no accesible u otro error: {e.faultString[:120]}")
    print("[ERROR] Ningún modelo candidato de Agentes fue accesible por XML-RPC.")
    print("        Esto invalidaría el diseño actual del kill-switch -- reportar de inmediato.")
    sys.exit(2)


def buscar_agente(models, db, uid, password, modelo, nombre):
    time.sleep(PAUSA_ENTRE_LLAMADAS_SEG)
    ids = models.execute_kw(
        db, uid, password, modelo, "search",
        [[["name", "=", nombre]]],
    )
    if not ids:
        print(f"[ERROR] No se encontró un Agente llamado '{nombre}'. Créalo primero (duplicar Hasky).")
        sys.exit(3)
    print(f"[OK] Agente '{nombre}' encontrado, id={ids[0]}")
    return ids[0]


def leer_estado(models, db, uid, password, modelo, agente_id):
    time.sleep(PAUSA_ENTRE_LLAMADAS_SEG)
    datos = models.execute_kw(
        db, uid, password, modelo, "read",
        [[agente_id]], {"fields": ["name", "active"]},
    )[0]
    print(f"[ESTADO] {datos['name']}: active={datos['active']}")
    return datos["active"]


def set_activo(models, db, uid, password, modelo, agente_id, valor):
    time.sleep(PAUSA_ENTRE_LLAMADAS_SEG)
    models.execute_kw(
        db, uid, password, modelo, "write",
        [[agente_id], {"active": valor}],
    )
    accion = "activado" if valor else "desactivado (archivado)"
    print(f"[ACCIÓN] Agente {accion} vía API externa.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", required=True, help="Ej: https://tuinstancia.odoo.com")
    ap.add_argument("--db", required=True)
    ap.add_argument("--user", required=True, help="Usuario de SERVICIO, no tu admin personal")
    ap.add_argument("--password", required=True)
    ap.add_argument("--agente", required=True, help="Nombre exacto del Agente de prueba")
    args = ap.parse_args()

    uid, models = conectar(args.url, args.db, args.user, args.password)
    modelo = detectar_modelo(models, args.db, uid, args.password)
    agente_id = buscar_agente(models, args.db, uid, args.password, modelo, args.agente)

    print("\n--- PASO 1: estado inicial ---")
    leer_estado(models, args.db, uid, args.password, modelo, agente_id)

    print("\n--- PASO 2: simular NO PAGO -> desactivar ---")
    set_activo(models, args.db, uid, args.password, modelo, agente_id, False)
    estado = leer_estado(models, args.db, uid, args.password, modelo, agente_id)
    assert estado is False, "El agente no quedó desactivado -- kill-switch NO funciona así."
    print("[VALIDADO] El agente quedó desactivado. Ahora prueba manualmente en el Live Chat")
    print("           público de esa base: el agente NO debería responder.")

    input("\nPresiona Enter cuando hayas confirmado en el Live Chat que el agente no responde...")

    print("\n--- PASO 3: simular PAGO RECIBIDO -> reactivar ---")
    set_activo(models, args.db, uid, args.password, modelo, agente_id, True)
    estado = leer_estado(models, args.db, uid, args.password, modelo, agente_id)
    assert estado is True, "El agente no se reactivó."
    print("[VALIDADO] El agente quedó reactivado.")

    print("\n=== RESULTADO ===")
    print("El mecanismo de kill-switch vía API externa (archivar/desarchivar) FUNCIONA.")
    print("Esto valida la pieza central del Módulo SaaS Efficax descrita en el RFD.")


if __name__ == "__main__":
    main()

# Fuente sobre límites de uso de la API externa de Odoo (cumplidos arriba
# con la pausa entre llamadas y el usuario de servicio dedicado):
# https://www.odoo.com/acceptable-use
