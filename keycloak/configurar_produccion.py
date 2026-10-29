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
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

REALM = "GlobalExchange"
CLIENT = "global-exchange-web"
TEMA_LOGIN = "global-exchange"


def leer_env(ruta):
    valores = {}
    with open(ruta, encoding="utf-8") as archivo:
        for linea in archivo:
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                clave, valor = linea.split("=", 1)
                valores[clave.strip()] = valor.strip()
    return valores


def pedir_json(url, *, metodo="GET", headers=None, params=None, data=None, timeout=30):
    if params:
        separador = "&" if "?" in url else "?"
        url = f"{url}{separador}{urllib.parse.urlencode(params)}"

    cuerpo = None
    cabeceras = dict(headers or {})
    if data is not None:
        if cabeceras.get("Content-Type") == "application/x-www-form-urlencoded":
            cuerpo = urllib.parse.urlencode(data).encode("utf-8")
        else:
            cabeceras["Content-Type"] = "application/json"
            cuerpo = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(url, data=cuerpo, headers=cabeceras, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as respuesta:
            bruto = respuesta.read().decode("utf-8", errors="replace")
            return respuesta.status, json.loads(bruto) if bruto else None, bruto
    except urllib.error.HTTPError as e:
        bruto = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(bruto) if bruto else None, bruto
        except json.JSONDecodeError:
            return e.code, None, bruto
    except urllib.error.URLError as e:
        sys.exit(f"No se pudo conectar con Keycloak: {e.reason}")


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

    estado, cuerpo, _ = pedir_json(
        f"{base}/realms/master/protocol/openid-connect/token",
        metodo="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_id": "admin-cli",
            "username": env.get("KC_BOOTSTRAP_ADMIN_USERNAME", "admin"),
            "password": env["KC_BOOTSTRAP_ADMIN_PASSWORD"],
            "grant_type": "password",
        },
        timeout=30,
    )
    token = (cuerpo or {}).get("access_token") if estado == 200 else None
    if not token:
        sys.exit(f"No se pudo entrar como administrador de Keycloak en {base}.")
    cabeceras = {"Authorization": f"Bearer {token}"}

    _, clientes, _ = pedir_json(
        f"{base}/admin/realms/{REALM}/clients",
        headers=cabeceras,
        params={"clientId": CLIENT},
        timeout=30,
    )
    if not clientes:
        sys.exit(f"No existe el client {CLIENT} en el realm {REALM}. ¿Se importó el realm?")
    client = clientes[0]

    # Volver al callback de OIDC y a la portada (a donde manda el logout).
    client["redirectUris"] = [f"{backend}/oidc/callback/", f"{backend}/"]
    client["webOrigins"] = [backend]
    client.setdefault("attributes", {})["post.logout.redirect.uris"] = "+"
    client["secret"] = env["KEYCLOAK_WEB_CLIENT_SECRET"]

    estado, _, bruto = pedir_json(
        f"{base}/admin/realms/{REALM}/clients/{client['id']}",
        metodo="PUT",
        headers=cabeceras,
        data=client,
        timeout=30,
    )
    if estado >= 400:
        sys.exit(f"Keycloak rechazó la configuración: {estado} {bruto[:200]}")

    # El administrador incluye a cajero y analista_cambiario (rol compuesto del
    # realm-export). Un Keycloak creado antes de ese cambio no reimporta el
    # realm, así que se asegura acá. Agregarlos de nuevo no cambia nada.
    roles = f"{base}/admin/realms/{REALM}/clients/{client['id']}/roles"
    incluidos = [pedir_json(f"{roles}/{nombre}", headers=cabeceras, timeout=30)[1]
                 for nombre in ("analista_cambiario", "cajero")]
    estado, _, bruto = pedir_json(
        f"{roles}/administrador/composites",
        metodo="POST",
        headers=cabeceras,
        data=incluidos,
        timeout=30,
    )
    if estado >= 400:
        sys.exit(f"Keycloak rechazó el rol compuesto: {estado} {bruto[:200]}")

    # El tema del inicio de sesión viene en el realm-export, pero un Keycloak
    # que ya tenía el realm no lo reimporta: se asegura acá.
    estado, _, bruto = pedir_json(
        f"{base}/admin/realms/{REALM}",
        metodo="PUT",
        headers=cabeceras,
        data={"loginTheme": TEMA_LOGIN, "displayName": "Global Exchange"},
        timeout=30,
    )
    if estado >= 400:
        sys.exit(f"Keycloak rechazó el tema: {estado} {bruto[:200]}")

    print(f"Client {CLIENT} configurado:")
    print(f"  vuelve a      {', '.join(client['redirectUris'])}")
    print(f"  secreto       el de KEYCLOAK_WEB_CLIENT_SECRET en {args.env_file}")
    print("  administrador incluye analista_cambiario y cajero")
    print(f"  inicio de sesión con el tema {TEMA_LOGIN}")


if __name__ == "__main__":
    main()
