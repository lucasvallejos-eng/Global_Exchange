"""Configura el client de Django en un Keycloak de producción.

El realm-export trae el client ``global-exchange-web`` pensado para
desarrollo: solo acepta volver a ``http://localhost:8000`` y su secreto viene
enmascarado (``**********``). En un servidor hay que decirle cuáles son las
direcciones reales y cargarle el secreto que usa Django; si no, Keycloak
rechaza el login con "Invalid redirect uri".

Lee todo de ``.env.prod`` (el mismo archivo que usa docker-compose.prod.yml).
Uso, desde la raíz del repositorio, con el ambiente ya levantado:

    python keycloak/configurar_produccion.py --env-file .env.prod

Se puede correr más de una vez: deja la configuración igual.
"""
import argparse
import sys

import requests

REALM = "GlobalExchange"
CLIENT = "global-exchange-web"


def leer_env(ruta):
    valores = {}
    with open(ruta, encoding="utf-8") as archivo:
        for linea in archivo:
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                clave, valor = linea.split("=", 1)
                valores[clave.strip()] = valor.strip()
    return valores


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--env-file", default=".env.prod")
    parser.add_argument(
        "--keycloak", help="URL para llegar a Keycloak desde esta máquina (por defecto, URL_KEYCLOAK)."
    )
    args = parser.parse_args()

    env = leer_env(args.env_file)
    faltan = [c for c in ("URL_BACKEND", "URL_KEYCLOAK", "KC_BOOTSTRAP_ADMIN_PASSWORD",
                          "KEYCLOAK_WEB_CLIENT_SECRET") if not env.get(c)]
    if faltan:
        sys.exit(f"Faltan en {args.env_file}: {', '.join(faltan)}")

    base = (args.keycloak or env["URL_KEYCLOAK"]).rstrip("/")
    backend = env["URL_BACKEND"].rstrip("/")

    respuesta = requests.post(
        f"{base}/realms/master/protocol/openid-connect/token",
        data={
            "client_id": "admin-cli",
            "username": env.get("KC_BOOTSTRAP_ADMIN_USERNAME", "admin"),
            "password": env["KC_BOOTSTRAP_ADMIN_PASSWORD"],
            "grant_type": "password",
        },
        timeout=30,
    )
    token = respuesta.json().get("access_token") if respuesta.ok else None
    if not token:
        sys.exit(f"No se pudo entrar como administrador de Keycloak en {base}.")
    cabeceras = {"Authorization": f"Bearer {token}"}

    clientes = requests.get(f"{base}/admin/realms/{REALM}/clients", headers=cabeceras,
                            params={"clientId": CLIENT}, timeout=30).json()
    if not clientes:
        sys.exit(f"No existe el client {CLIENT} en el realm {REALM}. ¿Se importó el realm?")
    client = clientes[0]

    # Volver al callback de OIDC y a la portada (a donde manda el logout).
    client["redirectUris"] = [f"{backend}/oidc/callback/", f"{backend}/"]
    client["webOrigins"] = [backend]
    client.setdefault("attributes", {})["post.logout.redirect.uris"] = "+"
    client["secret"] = env["KEYCLOAK_WEB_CLIENT_SECRET"]

    respuesta = requests.put(f"{base}/admin/realms/{REALM}/clients/{client['id']}",
                             headers=cabeceras, json=client, timeout=30)
    if not respuesta.ok:
        sys.exit(f"Keycloak rechazó la configuración: {respuesta.status_code} {respuesta.text[:200]}")

    print(f"Client {CLIENT} configurado:")
    print(f"  vuelve a      {', '.join(client['redirectUris'])}")
    print(f"  secreto       el de KEYCLOAK_WEB_CLIENT_SECRET en {args.env_file}")


if __name__ == "__main__":
    main()
