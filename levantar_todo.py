"""Levanta todo Global Exchange con un solo comando (o un solo Play en PyCharm).

Orden:
  1. Limpia y remueve contenedores/volúmenes antiguos de Keycloak (docker compose down -v).
  2. Borra todos los archivos .env existentes en el proyecto.
  3. Crea/reconstruye los .env desde sus plantillas (.env.example).
  4. Keycloak + Postgres + Mailpit  (docker compose up -d, en keycloak/)
  5. Espera a que el realm GlobalExchange responda en http://localhost:8080
  6. Obtiene y regenera automáticamente el Client Secret de Keycloak e inyecta en .env.
  7. Crea/asegura los usuarios de prueba en Keycloak con sus roles (administrador, analista_cambiario, cajero, cliente).
  8. Backend Django: Verifica/Crea .venv, instala requirements, realiza migrate + loaddata + runserver 8000
  9. Frontend (maqueta): pnpm dev en 8443
"""
import glob
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
BACKEND = RAIZ / "backend"
FRONTEND = RAIZ / "frontend"
KEYCLOAK = RAIZ / "keycloak"

ESPERA_KEYCLOAK_SEG = 180
PUERTOS = {8000: "backend", 8443: "frontend"}

ES_WINDOWS = os.name == "nt"

REALM_NOMBRE = "GlobalExchange"
CLIENT_NOMBRE = "global-exchange-web"
PASSWORD_DEMO = "Prueba2026!"

USUARIOS_PRUEBA = [
    ("admin.test", "admin.test@globalexchange.local", "Ana", "Administradora", "administrador"),
    ("analista.test", "analista.test@globalexchange.local", "Ana", "Analista", "analista_cambiario"),
    ("cajero.test", "cajero.test@globalexchange.local", "Carlos", "Cajero", "cajero"),
    ("cliente.test", "cliente.test@globalexchange.local", "Clara", "Cliente", "cliente"),
]

# La consola de Windows (cp1252) no puede imprimir algunos caracteres que usa
# Vite; mejor reemplazarlos que cortar el programa.
for flujo in (sys.stdout, sys.stderr):
    try:
        flujo.reconfigure(errors="replace")
    except AttributeError:
        pass


def realm_url():
    """El issuer de Keycloak que usa el backend: variable de entorno o
    backend/.env. Así funciona también si Keycloak está en otro puerto
    (p. ej. 8180 con un docker-compose.override.yml)."""
    issuer = os.environ.get("KEYCLOAK_ISSUER")
    if not issuer:
        try:
            from dotenv import dotenv_values
            issuer = dotenv_values(BACKEND / ".env").get("KEYCLOAK_ISSUER")
        except ImportError:
            issuer = None
    return (issuer or "http://localhost:8080/realms/GlobalExchange").rstrip("/")


def puerto_ocupado(puerto):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", puerto)) == 0


class _TrabajoWindows:
    """Job Object de Windows: al morir este proceso (Stop del IDE), Windows
    cierra también a todos los hijos y nietos, en vez de dejarlos huérfanos
    ocupando los puertos."""

    def __init__(self):
        import ctypes
        from ctypes import wintypes

        self.k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self.k32.CreateJobObjectW.restype = wintypes.HANDLE
        self.k32.OpenProcess.restype = wintypes.HANDLE
        self.handle = self.k32.CreateJobObjectW(None, None)

        class Limites(ctypes.Structure):
            _fields_ = [
                ("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD),
            ]

        class Contadores(ctypes.Structure):
            _fields_ = [(n, ctypes.c_uint64) for n in (
                "Read", "Write", "Other", "ReadBytes", "WriteBytes", "OtherBytes")]

        class LimitesExtendidos(ctypes.Structure):
            _fields_ = [
                ("BasicLimitInformation", Limites),
                ("IoInfo", Contadores),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t),
            ]

        info = LimitesExtendidos()
        info.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE
        self.k32.SetInformationJobObject(
            self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)  # 9 = ExtendedLimitInformation
        )

    def agregar(self, proc):
        h = self.k32.OpenProcess(0x0001 | 0x0100, False, proc.pid)  # TERMINATE | SET_QUOTA
        if h:
            self.k32.AssignProcessToJobObject(self.handle, h)
            self.k32.CloseHandle(h)


_trabajo = None


def log(msg):
    print(f"[levantar] {msg}", flush=True)


def http_json_request(url, method="GET", data=None, headers=None, timeout=30):
    """Realiza peticiones HTTP JSON/Form usando urllib estándar sin dependencias externas."""
    req_headers = dict(headers or {})
    req_body = None
    if data is not None:
        if isinstance(data, (dict, list)):
            if req_headers.get("Content-Type") == "application/x-www-form-urlencoded":
                req_body = urllib.parse.urlencode(data).encode("utf-8")
            else:
                req_headers.setdefault("Content-Type", "application/json")
                req_body = json.dumps(data).encode("utf-8")
        elif isinstance(data, str):
            req_body = data.encode("utf-8")
        elif isinstance(data, bytes):
            req_body = data

    req = urllib.request.Request(url, data=req_body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
            body = resp.read().decode("utf-8", errors="replace")
            resp_headers = dict(resp.headers)
            try:
                parsed_data = json.loads(body) if body.strip() else None
            except json.JSONDecodeError:
                parsed_data = body
            return status, parsed_data, resp_headers
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            parsed_data = json.loads(body) if body.strip() else None
        except json.JSONDecodeError:
            parsed_data = body
        return e.code, parsed_data, dict(e.headers)
    except Exception as e:
        return 0, str(e), {}


def obtener_token_admin_kc(base_url, usuario="admin", password="admin123"):
    """Obtiene el token de acceso de administrador usando el cliente admin-cli."""
    url = f"{base_url}/realms/master/protocol/openid-connect/token"
    status, data, _ = http_json_request(
        url,
        method="POST",
        data={
            "client_id": "admin-cli",
            "username": usuario,
            "password": password,
            "grant_type": "password",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if status == 200 and isinstance(data, dict) and "access_token" in data:
        return data["access_token"]
    raise RuntimeError(f"No se pudo autenticar como admin en Keycloak ({url}): status {status}, {data}")


def obtener_client_uuid_kc(base_url, realm, client_id_nombre, token):
    """Obtiene el UUID interno del client en Keycloak."""
    url = f"{base_url}/admin/realms/{realm}/clients?clientId={urllib.parse.quote(client_id_nombre)}"
    headers = {"Authorization": f"Bearer {token}"}
    status, data, _ = http_json_request(url, method="GET", headers=headers)
    if status == 200 and isinstance(data, list) and len(data) > 0:
        return data[0]["id"]
    raise RuntimeError(f"No se encontró el client '{client_id_nombre}' en el realm '{realm}'. Status {status}: {data}")


def obtener_o_regenerar_client_secret_kc(base_url, realm, client_uuid, token):
    """Genera/obtiene el secret del cliente en Keycloak."""
    headers = {"Authorization": f"Bearer {token}"}
    url_secret = f"{base_url}/admin/realms/{realm}/clients/{client_uuid}/client-secret"

    # Intentar regenerar un secreto fresco con POST
    status, data, _ = http_json_request(url_secret, method="POST", headers=headers)
    if status in (200, 201) and isinstance(data, dict) and data.get("value"):
        val = data["value"]
        if val != "**********":
            return val

    # Fallback a GET si no se pudo con POST
    status, data, _ = http_json_request(url_secret, method="GET", headers=headers)
    if status == 200 and isinstance(data, dict) and data.get("value"):
        return data["value"]

    raise RuntimeError(f"No se pudo obtener el Client Secret de Keycloak ({url_secret}): status {status}, {data}")


def asegurar_roles_y_usuarios_kc(base_url, realm, client_uuid, token):
    """Crea los roles necesarios en el client y asegura la existencia de los usuarios
    de prueba asignándoles sus respectivos roles y contraseña."""
    headers = {"Authorization": f"Bearer {token}"}
    roles_url = f"{base_url}/admin/realms/{realm}/clients/{client_uuid}/roles"

    # 1. Obtener lista de roles del client
    status, roles_data, _ = http_json_request(roles_url, method="GET", headers=headers)
    roles_dict = {}
    if status == 200 and isinstance(roles_data, list):
        for r in roles_data:
            roles_dict[r["name"]] = r

    # Roles necesarios según la especificación
    roles_necesarios = ["administrador", "analista_cambiario", "cajero", "cliente"]
    for rol_nom in roles_necesarios:
        if rol_nom not in roles_dict:
            log(f"Creando rol de client '{rol_nom}'...")
            http_json_request(roles_url, method="POST", data={"name": rol_nom}, headers=headers)
            status_r, r_obj, _ = http_json_request(f"{roles_url}/{urllib.parse.quote(rol_nom)}", method="GET", headers=headers)
            if status_r == 200 and isinstance(r_obj, dict):
                roles_dict[rol_nom] = r_obj

    # 2. Crear o actualizar usuarios
    log("Creando y configurando usuarios de prueba en Keycloak...")
    for username, email, nombre, apellido, rol_nom in USUARIOS_PRUEBA:
        # Verificar si el usuario ya existe
        users_query_url = f"{base_url}/admin/realms/{realm}/users?username={urllib.parse.quote(username)}&exact=true"
        status_u, users_list, _ = http_json_request(users_query_url, method="GET", headers=headers)

        uid = None
        if status_u == 200 and isinstance(users_list, list) and len(users_list) > 0:
            uid = users_list[0]["id"]
            log(f"  - Usuario '{username}' (rol: {rol_nom}): ya existía, actualizando credenciales y rol...")
        else:
            create_url = f"{base_url}/admin/realms/{realm}/users"
            user_payload = {
                "username": username,
                "email": email,
                "firstName": nombre,
                "lastName": apellido,
                "enabled": True,
                "emailVerified": True,
            }
            status_c, _, resp_h = http_json_request(create_url, method="POST", data=user_payload, headers=headers)
            if status_c == 201:
                loc = resp_h.get("Location") or resp_h.get("location")
                if loc:
                    uid = loc.rsplit("/", 1)[-1]
            if not uid:
                status_q, users_q, _ = http_json_request(users_query_url, method="GET", headers=headers)
                if status_q == 200 and isinstance(users_q, list) and len(users_q) > 0:
                    uid = users_q[0]["id"]
            log(f"  - Usuario '{username}' (rol: {rol_nom}): creado exitosamente.")

        if not uid:
            log(f"  - Error: no se pudo obtener el UID de '{username}'.")
            continue

        # Setear contraseña
        pwd_url = f"{base_url}/admin/realms/{realm}/users/{uid}/reset-password"
        http_json_request(
            pwd_url,
            method="PUT",
            data={"type": "password", "value": PASSWORD_DEMO, "temporary": False},
            headers=headers,
        )

        # Asignar rol del client
        rol_obj = roles_dict.get(rol_nom)
        if not rol_obj:
            status_r, rol_obj, _ = http_json_request(f"{roles_url}/{urllib.parse.quote(rol_nom)}", method="GET", headers=headers)
            if status_r == 200 and isinstance(rol_obj, dict):
                roles_dict[rol_nom] = rol_obj

        if rol_obj:
            assign_url = f"{base_url}/admin/realms/{realm}/users/{uid}/role-mappings/clients/{client_uuid}"
            http_json_request(assign_url, method="POST", data=[rol_obj], headers=headers)

    log(f"Usuarios de prueba listos. Contraseña para todos: '{PASSWORD_DEMO}'.")


def asegurar_venv_y_requirements():
    """Garantiza la existencia del .venv en backend e instala requirements.txt."""
    venv_dir = BACKEND / ".venv"
    sub_py = "Scripts/python.exe" if ES_WINDOWS else "bin/python"
    py_executable = venv_dir / sub_py

    # 1. Verificar/Crear entorno virtual (.venv)
    if not py_executable.exists():
        log(f"No se encontró un entorno virtual en {venv_dir}. Creando .venv...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        log("Entorno virtual .venv creado con éxito.")

    # 2. Verificar/Instalar requerimientos
    req_file = BACKEND / "requirements.txt"
    if req_file.exists():
        log("Instalando/verificando requerimientos del backend (requirements.txt)...")
        subprocess.run([str(py_executable), "-m", "pip", "install", "-r", str(req_file)], check=True)
    else:
        log("Aviso: No se encontró el archivo requirements.txt en backend/.")

    return str(py_executable)


def entorno_con_node():
    """PATH con node/pnpm. PyCharm no siempre carga nvm, así que lo buscamos."""
    env = os.environ.copy()
    if shutil.which("node", path=env.get("PATH")):
        return env
    nvm = os.environ.get("NVM_DIR", str(Path.home() / ".nvm"))
    versiones = sorted(glob.glob(os.path.join(nvm, "versions", "node", "*", "bin")))
    if versiones:
        env["PATH"] = versiones[-1] + os.pathsep + env.get("PATH", "")
    return env


def comando_pnpm(env):
    pnpm = shutil.which("pnpm", path=env.get("PATH"))
    if pnpm:
        return [pnpm]
    npx = shutil.which("npx", path=env.get("PATH"))
    if npx:
        return [npx, "pnpm"]
    sys.exit("[levantar] No encuentro node/pnpm. Instalá Node.js 20+ (o revisá nvm).")


def limpiar_docker_keycloak():
    """Detiene y elimina contenedores y volúmenes de Keycloak."""
    if shutil.which("docker"):
        log("Limpiando infraestructura previa de Keycloak (docker compose down -v)...")
        try:
            subprocess.run(["docker", "compose", "down", "-v"], cwd=KEYCLOAK, check=False)
        except Exception as e:
            log(f"Aviso al limpiar Docker: {e}")


def borrar_archivos_env():
    """Busca recursivamente todos los archivos .env en el proyecto y los borra."""
    log("Buscando y eliminando archivos .env previos...")

    ignorar_dirs = {".venv", "venv", "node_modules", ".git"}
    borrados = 0
    for root, dirs, files in os.walk(RAIZ):
        dirs[:] = [d for d in dirs if d not in ignorar_dirs]
        for file in files:
            if file == ".env":
                path_env = Path(root) / file
                try:
                    path_env.unlink()
                    log(f"  - Eliminado: {path_env.relative_to(RAIZ)}")
                    borrados += 1
                except Exception as e:
                    log(f"  - No se pudo eliminar {path_env}: {e}")

    if borrados == 0:
        log("No se encontraron archivos .env previos para borrar.")


def actualizar_o_crear_env(path_env: Path, path_example: Path, cambios: dict):
    """Crea el archivo .env desde su plantilla si no existe, y actualiza/agrega
    las variables indicadas en cambios."""
    if not path_env.exists():
        if path_example.exists():
            shutil.copy(path_example, path_env)
        else:
            path_env.touch()

    lineas = path_env.read_text(encoding="utf-8").splitlines() if path_env.exists() else []
    pendientes = dict(cambios)

    nuevas_lineas = []
    for linea in lineas:
        linea_strip = linea.strip()
        if linea_strip and not linea_strip.startswith("#") and "=" in linea:
            clave = linea.split("=", 1)[0].strip()
            if clave in pendientes:
                val = pendientes.pop(clave)
                linea = f"{clave}={val}"
        nuevas_lineas.append(linea)

    for clave, val in pendientes.items():
        nuevas_lineas.append(f"{clave}={val}")

    path_env.write_text("\n".join(nuevas_lineas) + "\n", encoding="utf-8")


def fase1_preparar_envs():
    """Fase 1: Creación y Verificación Previa de .env.
    Crea los .env que falten e inyecta credenciales fijas de admin en Keycloak."""
    log("Fase 1: Recreando y preparando archivos .env...")

    # Keycloak .env
    kc_changes = {
        "KEYCLOAK_ADMIN": "admin",
        "KEYCLOAK_ADMIN_PASSWORD": "admin123",
        "KC_BOOTSTRAP_ADMIN_USERNAME": "admin",
        "KC_BOOTSTRAP_ADMIN_PASSWORD": "admin123",
        "POSTGRES_PASSWORD": "admin123",
    }
    actualizar_o_crear_env(KEYCLOAK / ".env", KEYCLOAK / ".env.example", kc_changes)

    # Backend .env
    actualizar_o_crear_env(BACKEND / ".env", BACKEND / ".env.example", {})

    # Frontend .env
    frontend_example = FRONTEND / ".env.example" if (FRONTEND / ".env.example").exists() else RAIZ / ".env.example"
    actualizar_o_crear_env(FRONTEND / ".env", frontend_example, {})

    # Root .env
    actualizar_o_crear_env(RAIZ / ".env", RAIZ / ".env.example", {})
    log("Archivos .env recreados y credenciales fijas inyectadas (Keycloak: admin / admin123).")


def fase2_infraestructura_y_secret():
    """Fase 2: Levanta infraestructura, obtiene automáticamente el Client Secret
    y crea los usuarios con sus roles en Keycloak."""
    if not shutil.which("docker"):
        sys.exit("[levantar] No encuentro docker en el PATH.")

    log("Fase 2: Levantando infraestructura (docker compose up -d)...")
    subprocess.run(["docker", "compose", "up", "-d"], cwd=KEYCLOAK, check=True)

    url = realm_url()
    log(f"Esperando a que Keycloak responda en {url} ...")
    limite = time.time() + ESPERA_KEYCLOAK_SEG
    keycloak_listo = False
    while time.time() < limite:
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                if r.status == 200:
                    log("Keycloak listo.")
                    keycloak_listo = True
                    break
        except Exception:
            pass
        time.sleep(2)

    if not keycloak_listo:
        sys.exit(f"[levantar] Keycloak no respondió a tiempo en {url}. Abortando.")

    base_url = url.split("/realms/")[0] if "/realms/" in url else "http://localhost:8080"
    realm = url.split("/realms/")[1] if "/realms/" in url else REALM_NOMBRE

    log("Autenticando contra la API de administración de Keycloak...")
    admin_user = "admin"
    admin_password = "admin123"
    token = obtener_token_admin_kc(base_url, admin_user, admin_password)

    log(f"Obteniendo identificador del client '{CLIENT_NOMBRE}'...")
    client_uuid = obtener_client_uuid_kc(base_url, realm, CLIENT_NOMBRE, token)

    log("Generando/obteniendo nuevo Client Secret de Keycloak...")
    client_secret = obtener_o_regenerar_client_secret_kc(base_url, realm, client_uuid, token)
    log(f"Client Secret obtenido exitosamente: {client_secret[:6]}...{client_secret[-4:]}")

    secret_changes = {
        "KEYCLOAK_CLIENT_SECRET": client_secret,
        "KEYCLOAK_WEB_CLIENT_SECRET": client_secret,
    }

    actualizar_o_crear_env(BACKEND / ".env", BACKEND / ".env.example", secret_changes)
    actualizar_o_crear_env(FRONTEND / ".env", FRONTEND / ".env.example", secret_changes)
    actualizar_o_crear_env(RAIZ / ".env", RAIZ / ".env.example", secret_changes)
    log("KEYCLOAK_CLIENT_SECRET inyectado automáticamente en los archivos .env.")

    # Creación automática de usuarios y asignación de roles
    asegurar_roles_y_usuarios_kc(base_url, realm, client_uuid, token)


def reenviar_salida(proc, prefijo):
    for linea in iter(proc.stdout.readline, ""):
        print(f"[{prefijo}] {linea}", end="", flush=True)


def lanzar(cmd, cwd, prefijo, env=None):
    kwargs = {}
    if ES_WINDOWS:
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(
        cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1, encoding="utf-8", errors="replace", **kwargs,
    )
    if _trabajo is not None:
        _trabajo.agregar(proc)
    threading.Thread(target=reenviar_salida, args=(proc, prefijo), daemon=True).start()
    return proc


def detener(procesos):
    for proc in procesos:
        if proc.poll() is not None:
            continue
        try:
            if ES_WINDOWS:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
            else:
                os.killpg(proc.pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
    for proc in procesos:
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            if not ES_WINDOWS:
                os.killpg(proc.pid, signal.SIGKILL)


def main():
    global _trabajo
    ocupados = [f"{p} ({nombre})" for p, nombre in PUERTOS.items() if puerto_ocupado(p)]
    if ocupados:
        sys.exit(
            f"[levantar] Puertos ocupados: {', '.join(ocupados)}. ¿Quedó corriendo una "
            "ejecución anterior? Cerrala (o matá el proceso) y volvé a intentar."
        )
    if ES_WINDOWS:
        try:
            _trabajo = _TrabajoWindows()
        except Exception as error:
            log(f"Aviso: no se pudo crear el Job Object de Windows ({error}).")

    # 1. Bajar y limpiar contenedores/volúmenes antiguos de Keycloak
    limpiar_docker_keycloak()

    # 2. Borrado de todos los archivos .env existentes
    borrar_archivos_env()

    # 3. Fase 1: Creación y Verificación Previa de .env
    fase1_preparar_envs()

    # 4. Fase 2: Levantar Infraestructura, Obtener Secret y Crear Usuarios
    fase2_infraestructura_y_secret()

    # 5. Fase 3: Arranque de Servicios Restantes
    log("Fase 3: Arrancando servicios restantes (Backend + Frontend)...")

    # Garantizar que el .venv exista y tenga sus dependencias
    py = asegurar_venv_y_requirements()

    env_py = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
    log("Aplicando migraciones...")
    subprocess.run([py, "manage.py", "migrate", "--noinput"], cwd=BACKEND, env=env_py, check=True)

    demo_fixture = BACKEND / "fixtures" / "demo.json"
    if demo_fixture.exists():
        log("Cargando datos iniciales de prueba (fixtures/demo.json)...")
        try:
            subprocess.run([py, "manage.py", "loaddata", "fixtures/demo.json"], cwd=BACKEND, env=env_py, check=False)
        except Exception as e:
            log(f"Aviso al cargar fixtures: {e}")

    env_node = entorno_con_node()
    pnpm = comando_pnpm(env_node)
    if not (FRONTEND / "node_modules").exists():
        log("Instalando dependencias del frontend (pnpm install)...")
        subprocess.run(pnpm + ["install"], cwd=FRONTEND, env=env_node, check=True)

    procesos = [
        lanzar([py, "manage.py", "runserver", "8000"], BACKEND, "backend", env_py),
        lanzar(pnpm + ["dev"], FRONTEND, "frontend", env_node),
    ]

    def al_recibir_senal(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, al_recibir_senal)

    print("\n" + "=" * 70)
    log("¡Global Exchange levantado con éxito!")
    print("  - Backend (Django):   http://localhost:8000")
    print("  - Frontend (Maqueta): http://localhost:8443")
    print("  - Keycloak:           http://localhost:8080  (admin / admin123)")
    print("  - Mailpit:            http://localhost:8025")
    print()
    print("Usuarios de prueba creados (contraseña para todos: Prueba2026!):")
    print("  - admin.test    -> rol: administrador")
    print("  - analista.test -> rol: analista_cambiario")
    print("  - cajero.test   -> rol: cajero")
    print("  - cliente.test  -> rol: cliente")
    print("=" * 70 + "\n")
    log("Entrá por http://localhost:8000 . Presiona Stop o Ctrl+C para detener backend y frontend.")
    try:
        while True:
            for proc, nombre in zip(procesos, ("backend", "frontend")):
                if proc.poll() is not None:
                    log(f"El {nombre} terminó (código {proc.returncode}); cierro el resto.")
                    return proc.returncode or 1
            time.sleep(1)
    except KeyboardInterrupt:
        log("Cerrando backend y frontend...")
        return 0
    finally:
        detener(procesos)


if __name__ == "__main__":
    sys.exit(main())