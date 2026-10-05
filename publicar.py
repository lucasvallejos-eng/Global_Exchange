"""Publica Global Exchange en internet con un solo comando.

Levanta el ambiente de producción (docker-compose.prod.yml) más dos túneles de
Cloudflare (docker-compose.publico.yml), que dan direcciones https públicas
sin servidor propio, sin cuenta y sin abrir puertos. Al terminar imprime el
link para entrar.

Uso, desde la raíz del repositorio y con Docker Desktop abierto:
    backend\\.venv\\Scripts\\python publicar.py           # Windows
    backend/.venv/bin/python publicar.py                 # Linux/Mac

    publicar.py --demo     además crea un usuario por rol y carga datos de ejemplo
    publicar.py --apagar   baja todo (los datos quedan guardados en los volúmenes)

Las direcciones cambian cada vez que se crean los túneles: después de apagar,
se vuelve a correr este script y da otras. Mientras los túneles sigan
corriendo, volver a correrlo no las cambia.
"""
import argparse
import json
import re
import secrets
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ENV = RAIZ / ".env.prod"
EJEMPLO = RAIZ / ".env.prod.example"
COMPOSE = ["docker", "compose", "-f", "docker-compose.prod.yml",
           "-f", "docker-compose.publico.yml", "--env-file", ".env.prod"]
PATRON_URL = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")

# Se generan solas la primera vez y después no se tocan: la base de Keycloak
# queda creada con POSTGRES_PASSWORD y no aceptaría otra.
CLAVES = ("DJANGO_SECRET_KEY", "KC_BOOTSTRAP_ADMIN_PASSWORD", "POSTGRES_PASSWORD",
          "KEYCLOAK_WEB_CLIENT_SECRET")

for flujo in (sys.stdout, sys.stderr):
    try:
        flujo.reconfigure(errors="replace")
    except AttributeError:
        pass


def log(mensaje):
    print(f"[publicar] {mensaje}", flush=True)


def compose(*args, capturar=False):
    r = subprocess.run(COMPOSE + list(args), cwd=RAIZ, text=True, encoding="utf-8",
                       errors="replace", capture_output=capturar)
    if r.returncode != 0:
        if capturar:
            print(r.stdout, r.stderr)
        sys.exit(f"[publicar] Falló: docker compose {' '.join(args)}")
    return (r.stdout + r.stderr) if capturar else None


def leer_env():
    valores = {}
    for linea in ENV.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea and not linea.startswith("#") and "=" in linea:
            clave, valor = linea.split("=", 1)
            valores[clave.strip()] = valor.strip()
    return valores


def escribir_env(cambios):
    """Reemplaza (o agrega) estas variables sin tocar el resto del archivo."""
    lineas = ENV.read_text(encoding="utf-8").splitlines()
    pendientes = dict(cambios)
    for i, linea in enumerate(lineas):
        clave = linea.split("=", 1)[0].strip()
        if "=" in linea and not linea.lstrip().startswith("#") and clave in pendientes:
            lineas[i] = f"{clave}={pendientes.pop(clave)}"
    lineas += [f"{clave}={valor}" for clave, valor in pendientes.items()]
    ENV.write_text("\n".join(lineas) + "\n", encoding="utf-8")


def asegurar_env():
    if ENV.exists():
        return
    ENV.write_text(EJEMPLO.read_text(encoding="utf-8"), encoding="utf-8")
    escribir_env({clave: secrets.token_urlsafe(32) for clave in CLAVES})
    log(f"Creado {ENV.name} con claves nuevas (está en .gitignore, no se sube).")


def direccion_tunel(servicio, espera=90):
    """La dirección pública que Cloudflare le dio al túnel (sale en su log)."""
    limite = time.time() + espera
    while time.time() < limite:
        encontradas = [u for u in PATRON_URL.findall(compose("logs", "--no-color", servicio, capturar=True))
                       if not u.startswith("https://api.")]
        if encontradas:
            return encontradas[-1]
        time.sleep(2)
    sys.exit(f"[publicar] El túnel {servicio} no dio dirección. "
             f"Mirá su log: docker compose -f docker-compose.prod.yml "
             f"-f docker-compose.publico.yml --env-file .env.prod logs {servicio}")


def esperar(url, espera=300):
    limite = time.time() + espera
    while time.time() < limite:
        try:
            with urllib.request.urlopen(url, timeout=5) as respuesta:
                if respuesta.status == 200:
                    return
        except Exception:
            pass
        time.sleep(3)
    sys.exit(f"[publicar] {url} no respondió a tiempo.")


def esperar_dns(url, espera=120):
    """Espera a que la dirección nueva exista en el DNS. Se pregunta a
    Cloudflare directamente: si se preguntara a la PC antes de tiempo, Windows
    guardaría el "no existe" unos minutos y el link no abriría."""
    host = urllib.parse.urlparse(url).hostname
    consulta = "https://cloudflare-dns.com/dns-query?" + urllib.parse.urlencode({"name": host, "type": "A"})
    limite = time.time() + espera
    while time.time() < limite:
        try:
            pedido = urllib.request.Request(consulta, headers={"accept": "application/dns-json"})
            with urllib.request.urlopen(pedido, timeout=5) as respuesta:
                if json.load(respuesta).get("Answer"):
                    return True
        except Exception:
            pass
        time.sleep(3)
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--demo", action="store_true", help="crea un usuario por rol y carga datos de ejemplo")
    parser.add_argument("--apagar", action="store_true", help="baja todo (los datos quedan)")
    args = parser.parse_args()

    if subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
        sys.exit("[publicar] Docker no responde. Abrí Docker Desktop y probá de nuevo.")
    asegurar_env()

    if args.apagar:
        compose("down")
        log("Apagado. Los datos quedan en los volúmenes; la próxima vez las direcciones serán otras.")
        return

    log("Abriendo los túneles...")
    compose("up", "-d", "tunel-app", "tunel-keycloak")
    url_app = direccion_tunel("tunel-app")
    url_kc = direccion_tunel("tunel-keycloak")
    log(f"Aplicación: {url_app}")
    log(f"Keycloak:   {url_kc}")

    escribir_env({
        "URL_BACKEND": url_app,
        "URL_MAQUETA": f"{url_app}/app",
        "URL_KEYCLOAK": url_kc,
        "DJANGO_ALLOWED_HOSTS": ".trycloudflare.com",
        "DJANGO_HTTPS": "1",
    })

    log("Levantando el sistema (la primera vez tarda unos minutos)...")
    compose("up", "-d", "--build")

    env = leer_env()
    kc_local = f"http://127.0.0.1:{env.get('PUERTO_KEYCLOAK_LOCAL', '18080')}"
    log("Esperando a Keycloak...")
    esperar(f"{kc_local}/realms/GlobalExchange")

    subprocess.run([sys.executable, "keycloak/configurar_produccion.py", "--env-file", ".env.prod",
                    "--keycloak", kc_local], cwd=RAIZ, check=True)

    if args.demo:
        subprocess.run([sys.executable, "keycloak/crear_usuarios_prueba.py", "--url", kc_local,
                        "--admin-user", env.get("KC_BOOTSTRAP_ADMIN_USERNAME", "admin"),
                        "--admin-password", env["KC_BOOTSTRAP_ADMIN_PASSWORD"]], cwd=RAIZ, check=True)
        cargado = subprocess.run(COMPOSE + ["exec", "-T", "backend", "python", "manage.py", "loaddata",
                                            "fixtures/demo.json"], cwd=RAIZ, capture_output=True)
        log("Datos de ejemplo cargados." if cargado.returncode == 0
            else "Los datos de ejemplo ya estaban cargados (no se tocaron).")

    log("Esperando a que las direcciones se publiquen en internet...")
    if not (esperar_dns(url_app) and esperar_dns(url_kc)):
        log("Cloudflare todavía no publicó las direcciones; si el link no abre, esperá un minuto.")

    print(f"""
==============================================================
  Global Exchange está en internet. Entrá (y compartí):

      {url_app}

  Maqueta:   {url_app}/app/
  Keycloak:  {url_kc}   (admin: los datos están en .env.prod)

  Para apagar:  {comando_python()} publicar.py --apagar
==============================================================""", flush=True)


def comando_python():
    """Cómo se llamó a este Python, para repetirlo en el mensaje final: en
    Windows "python" a secas suele abrir la Microsoft Store."""
    try:
        return str(Path(sys.executable).relative_to(RAIZ)).removesuffix(".exe")
    except ValueError:
        return "python"


if __name__ == "__main__":
    main()
