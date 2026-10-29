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
corriendo, volver a correrlo no las cambia; si Cloudflare los dio de baja (la
PC se suspendió o se quedó sin internet un rato largo), los crea de nuevo.
"""
import argparse
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
ENV = RAIZ / ".env.prod"
EJEMPLO = RAIZ / ".env.prod.example"

try:
    from inyectar_credenciales import inyectar_credenciales
except ImportError:
    sys.path.insert(0, str(RAIZ))
    from inyectar_credenciales import inyectar_credenciales

COMPOSE = ["docker", "compose", "-f", "docker-compose.prod.yml",
           "-f", "docker-compose.publico.yml", "--env-file", ".env.prod"]
PATRON_URL = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")

# Se generan solas la primera vez y después no se tocan: la base de Keycloak
# queda creada con POSTGRES_PASSWORD y no aceptaría otra.
CLAVES = ("DJANGO_SECRET_KEY", "KC_BOOTSTRAP_ADMIN_PASSWORD", "POSTGRES_PASSWORD",
          "KEYCLOAK_WEB_CLIENT_SECRET")
STRIPE = ("STRIPE_PUBLISHABLE_KEY", "STRIPE_SECRET_KEY")

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


def leer_env(ruta=None):
    valores = {}
    for linea in (ruta or ENV).read_text(encoding="utf-8").splitlines():
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


def copiar_claves_stripe():
    """Si .env.prod no tiene las claves de Stripe, las toma de
    backend/.env.stripe (el de desarrollo). Sin ellas no se paga con tarjeta."""
    origen = RAIZ / "backend" / ".env.stripe"
    faltan = [c for c in STRIPE if not leer_env().get(c)]
    if not faltan or not origen.exists():
        return
    cambios = {c: v for c, v in leer_env(origen).items() if c in faltan and v}
    if cambios:
        escribir_env(cambios)
        log("Claves de Stripe copiadas de backend/.env.stripe.")


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


def tunel_caido(servicio):
    """Si Cloudflare dio de baja el túnel aunque su contenedor siga corriendo.

    Pasa cuando el túnel pierde la conexión un rato largo (la PC se suspendió
    o se quedó sin internet): al volver, Cloudflare ya no lo reconoce y la
    dirección que figura en el log dejó de existir.
    """
    return "Tunnel not found" in compose("logs", "--no-color", "--tail", "20", servicio, capturar=True)


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


def python_con_requests():
    """Python para scripts auxiliares: prioriza backend/.venv si tiene requests."""
    candidatos = []
    venv = RAIZ / "backend" / ".venv"
    if os.name == "nt":
        candidatos.append(venv / "Scripts" / "python.exe")
    else:
        candidatos.append(venv / "bin" / "python")
    candidatos.append(Path(sys.executable))

    for python in candidatos:
        if not python.exists():
            continue
        prueba = subprocess.run([str(python), "-c", "import requests"], capture_output=True)
        if prueba.returncode == 0:
            return str(python)
    sys.exit("[publicar] Falta 'requests' para configurar Keycloak. "
             "Usá backend/.venv/Scripts/python publicar.py o instalá backend/requirements.txt.")


def direcciones_dns_locales():
    """Nombres e IPs de la máquina donde corre el script (sin duplicados)."""
    candidatas = []
    hostname = socket.gethostname().strip()
    fqdn = socket.getfqdn().strip()
    if hostname:
        candidatas.append(hostname)
    if fqdn and fqdn != hostname:
        candidatas.append(fqdn)
    for nombre in (hostname, fqdn):
        if not nombre:
            continue
        try:
            for _, _, _, _, sockaddr in socket.getaddrinfo(nombre, None, family=socket.AF_INET):
                ip = sockaddr[0]
                if ip and not ip.startswith("127."):
                    candidatas.append(ip)
        except socket.gaierror:
            pass
    try:
        # Fuerza a elegir la interfaz de salida sin enviar tráfico real.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip_salida = s.getsockname()[0]
            if ip_salida and not ip_salida.startswith("127."):
                candidatas.append(ip_salida)
    except OSError:
        pass
    vistas, unicas = set(), []
    for valor in ["localhost", "127.0.0.1", *candidatas]:
        normalizado = valor.lower()
        if normalizado and normalizado not in vistas:
            vistas.add(normalizado)
            unicas.append(valor)
    return unicas


def main():
    # 0. Verificación mandatoria de credenciales.rar
    if not (RAIZ / "credenciales.rar").exists():
        sys.exit(
            "[publicar] ERROR: No se encontró el archivo 'credenciales.rar' en la raíz del proyecto. "
            "El programa presentará problemas si no se tiene el archivo de credenciales.rar."
        )

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
    if tunel_caido("tunel-app") or tunel_caido("tunel-keycloak"):
        log("Los túneles anteriores ya no existen en Cloudflare: se crean de nuevo (cambian las direcciones).")
        compose("up", "-d", "--force-recreate", "tunel-app", "tunel-keycloak")
    url_app = direccion_tunel("tunel-app")
    url_kc = direccion_tunel("tunel-keycloak")
    dns_locales = direcciones_dns_locales()
    log(f"Aplicación: {url_app}")
    log(f"Keycloak:   {url_kc}")
    log("Servidor local detectado en: " + ", ".join(dns_locales))

    escribir_env({
        "URL_BACKEND": url_app,
        "URL_MAQUETA": f"{url_app}/app",
        "URL_KEYCLOAK": url_kc,
        "DJANGO_ALLOWED_HOSTS": ",".join([".trycloudflare.com", *dns_locales]),
        "DJANGO_HTTPS": "1",
    })
    inyectar_credenciales(RAIZ, log_fn=log, archivo_prod=ENV)
    copiar_claves_stripe()

    log("Levantando el sistema (la primera vez tarda unos minutos)...")
    compose("up", "-d", "--build")

    env = leer_env()
    kc_local = f"http://127.0.0.1:{env.get('PUERTO_KEYCLOAK_LOCAL', '18080')}"
    python_aux = python_con_requests()
    log("Esperando a Keycloak...")
    esperar(f"{kc_local}/realms/GlobalExchange")

    subprocess.run([python_aux, "keycloak/configurar_produccion.py", "--env-file", ".env.prod",
                    "--keycloak", kc_local], cwd=RAIZ, check=True)

    if args.demo:
        subprocess.run([python_aux, "keycloak/crear_usuarios_prueba.py", "--url", kc_local,
                        "--admin-user", env.get("KC_BOOTSTRAP_ADMIN_USERNAME", "admin"),
                        "--admin-password", env["KC_BOOTSTRAP_ADMIN_PASSWORD"]], cwd=RAIZ, check=True)
        cargado = subprocess.run(COMPOSE + ["exec", "-T", "backend", "python", "manage.py", "loaddata",
                                            "fixtures/demo.json"], cwd=RAIZ, capture_output=True)
        log("Datos de ejemplo cargados." if cargado.returncode == 0
            else "Los datos de ejemplo ya estaban cargados (no se tocaron).")

    log("Esperando a que las direcciones se publiquen en internet...")
    if not (esperar_dns(url_app) and esperar_dns(url_kc)):
        log("Cloudflare todavía no publicó las direcciones; si el link no abre, esperá un minuto.")

    puerto_backend = env.get("PUERTO_BACKEND", "8000")
    accesos_locales = [f"http://{host}:{puerto_backend}" for host in dns_locales]

    print(f"""
==============================================================
  Global Exchange está en internet. Entrá (y compartí):

      {url_app}

  Maqueta:   {url_app}/app/
  Keycloak:  {url_kc}   (admin: los datos están en .env.prod)
  Servidor local: {", ".join(accesos_locales)}

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
