"""Crea los cuatro usuarios de prueba (uno por rol) en un Keycloak recién
levantado.

No es parte del sistema: es una herramienta de desarrollo. El realm-export no
trae usuarios a propósito (las contraseñas no se exportan), así que cada
Keycloak nuevo -una laptop distinta, una reinstalación- arranca sin ninguno.
Sin esto hay que crearlos a mano, pantalla por pantalla, cada vez.

Usa `requests`, que ya está instalado como dependencia de mozilla-django-oidc.

Uso, desde Global_Exchange/keycloak, con Keycloak ya arriba:

    ../backend/.venv/Scripts/python crear_usuarios_prueba.py

Por defecto lee la URL y las credenciales de admin de las variables de
entorno que ya usa docker-compose (KC_BOOTSTRAP_ADMIN_USERNAME/PASSWORD). Si
no están en el entorno, pasalas por parámetro:

    ../backend/.venv/Scripts/python crear_usuarios_prueba.py --admin-password admin_dev_2026
"""
import argparse
import os
import sys

import requests

REALM = "GlobalExchange"
CLIENT = "global-exchange-web"
PASSWORD_DEMO = "Prueba2026!"

USUARIOS = [
    ("admin.test", "admin.test@globalexchange.local", "Ana", "Administradora", "administrador"),
    ("analista.test", "analista.test@globalexchange.local", "Ana", "Analista", "analista_cambiario"),
    ("cajero.test", "cajero.test@globalexchange.local", "Carlos", "Cajero", "cajero"),
    ("cliente.test", "cliente.test@globalexchange.local", "Clara", "Cliente", "cliente"),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default=os.environ.get("KEYCLOAK_URL", "http://localhost:8080"))
    parser.add_argument("--admin-user", default=os.environ.get("KC_BOOTSTRAP_ADMIN_USERNAME", "admin"))
    parser.add_argument("--admin-password", default=os.environ.get("KC_BOOTSTRAP_ADMIN_PASSWORD"))
    args = parser.parse_args()

    if not args.admin_password:
        sys.exit(
            "Falta la contraseña del admin de Keycloak. Pasala con --admin-password "
            "o exportá KC_BOOTSTRAP_ADMIN_PASSWORD (está en keycloak/.env)."
        )

    token_resp = requests.post(
        f"{args.url}/realms/master/protocol/openid-connect/token",
        data={
            "client_id": "admin-cli",
            "username": args.admin_user,
            "password": args.admin_password,
            "grant_type": "password",
        },
    )
    token = token_resp.json().get("access_token")
    if not token:
        sys.exit(f"No se pudo autenticar contra Keycloak ({args.url}). Revisá URL y credenciales.")
    h = {"Authorization": f"Bearer {token}"}

    clientes = requests.get(f"{args.url}/admin/realms/{REALM}/clients", headers=h).json()
    web = next((c for c in clientes if c["clientId"] == CLIENT), None)
    if web is None:
        sys.exit(f"No encontré el client '{CLIENT}' en el realm '{REALM}'. ¿Se importó el realm-export?")
    client_id = web["id"]

    def set_password(uid):
        requests.put(
            f"{args.url}/admin/realms/{REALM}/users/{uid}/reset-password",
            headers=h,
            json={"type": "password", "value": PASSWORD_DEMO, "temporary": False},
        )

    def assign_role(uid, nombre_rol):
        rol = requests.get(
            f"{args.url}/admin/realms/{REALM}/clients/{client_id}/roles/{nombre_rol}", headers=h
        ).json()
        requests.post(
            f"{args.url}/admin/realms/{REALM}/users/{uid}/role-mappings/clients/{client_id}",
            headers=h,
            json=[rol],
        )

    for username, email, nombre, apellido, rol in USUARIOS:
        existentes = requests.get(
            f"{args.url}/admin/realms/{REALM}/users",
            headers=h,
            params={"username": username, "exact": "true"},
        ).json()
        if existentes:
            uid = existentes[0]["id"]
            print(f"{username} -> ya existía, reasigno contraseña y rol")
        else:
            resp = requests.post(
                f"{args.url}/admin/realms/{REALM}/users",
                headers=h,
                json={
                    "username": username,
                    "email": email,
                    "firstName": nombre,
                    "lastName": apellido,
                    "enabled": True,
                    "emailVerified": True,
                },
            )
            uid = resp.headers["Location"].rsplit("/", 1)[-1]
            print(f"{username} -> creado")
        set_password(uid)
        assign_role(uid, rol)

    print(f"\nContraseña para los cuatro usuarios: {PASSWORD_DEMO}")


if __name__ == "__main__":
    main()
