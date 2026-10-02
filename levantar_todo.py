"""Levanta todo Global Exchange con un solo comando (o un solo Play en PyCharm).

Orden:
  1. Keycloak + Postgres + Mailpit  (docker compose up -d, en keycloak/)
  2. Espera a que el realm GlobalExchange responda en http://localhost:8080
  3. Backend Django: migrate + runserver 8000
  4. Frontend (maqueta): pnpm dev en 8443

Backend y frontend corren como procesos hijos y su salida se muestra en esta
misma consola con un prefijo [backend] / [frontend]. Al detenerlo (Stop en
PyCharm o Ctrl+C) se cierran ambos. Los contenedores de Keycloak quedan
corriendo para que el próximo arranque sea inmediato; para apagarlos:
    cd keycloak && docker compose stop

La URL de Keycloak se toma de KEYCLOAK_ISSUER (variable de entorno o
backend/.env), así que sirve también con Keycloak en otro puerto.

Uso (o el botón Play de PyCharm / F5 de VS Code, ver
docs/conversaciones-ia/2026-10-02-fixes-pre-tag.md):
    backend/.venv/bin/python levantar_todo.py          # Linux/Mac
    backend\\.venv\\Scripts\\python levantar_todo.py   # Windows
"""
import glob
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
BACKEND = RAIZ / "backend"
FRONTEND = RAIZ / "frontend"
KEYCLOAK = RAIZ / "keycloak"

ESPERA_KEYCLOAK_SEG = 180
PUERTOS = {8000: "backend", 8443: "frontend"}

ES_WINDOWS = os.name == "nt"

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


def python_backend():
    """Intérprete del venv del backend (o el actual si no existe)."""
    sub = "Scripts/python.exe" if ES_WINDOWS else "bin/python"
    candidato = BACKEND / ".venv" / sub
    return str(candidato) if candidato.exists() else sys.executable


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


def levantar_keycloak():
    if not shutil.which("docker"):
        sys.exit("[levantar] No encuentro docker en el PATH.")
    if not (KEYCLOAK / ".env").exists():
        sys.exit("[levantar] Falta keycloak/.env (copiá keycloak/.env.example y completalo).")
    log("Levantando Keycloak (docker compose up -d)...")
    subprocess.run(["docker", "compose", "up", "-d"], cwd=KEYCLOAK, check=True)

    url = realm_url()
    log(f"Esperando a que Keycloak responda en {url} ...")
    limite = time.time() + ESPERA_KEYCLOAK_SEG
    while time.time() < limite:
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                if r.status == 200:
                    log("Keycloak listo.")
                    return
        except Exception:
            pass
        time.sleep(2)
    sys.exit("[levantar] Keycloak no respondió a tiempo. Mirá: cd keycloak && docker compose logs keycloak")


def reenviar_salida(proc, prefijo):
    for linea in iter(proc.stdout.readline, ""):
        print(f"[{prefijo}] {linea}", end="", flush=True)


def lanzar(cmd, cwd, prefijo, env=None):
    kwargs = {}
    if ES_WINDOWS:
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        # Grupo de procesos propio: al cerrar matamos también a los nietos
        # (el autoreloader de Django, vite lanzado por pnpm, etc.).
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
        except Exception as error:  # sin el job igual funciona; solo limpia peor
            log(f"Aviso: no se pudo crear el Job Object de Windows ({error}).")

    levantar_keycloak()

    py = python_backend()
    env_py = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"}
    log("Aplicando migraciones...")
    subprocess.run([py, "manage.py", "migrate", "--noinput"], cwd=BACKEND, env=env_py, check=True)

    env_node = entorno_con_node()
    pnpm = comando_pnpm(env_node)
    if not (FRONTEND / "node_modules").exists():
        log("Instalando dependencias del frontend (pnpm install)...")
        subprocess.run(pnpm + ["install"], cwd=FRONTEND, env=env_node, check=True)

    procesos = [
        lanzar([py, "manage.py", "runserver", "8000"], BACKEND, "backend", env_py),
        lanzar(pnpm + ["dev"], FRONTEND, "frontend", env_node),
    ]

    # PyCharm manda SIGTERM/SIGINT al apretar Stop: lo convertimos en salida limpia.
    def al_recibir_senal(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, al_recibir_senal)

    log("Todo arriba:  Keycloak http://localhost:8080  |  "
        "Backend http://localhost:8000  |  Maqueta http://localhost:8443")
    log("Entrá por http://localhost:8000 . Stop / Ctrl+C para cerrar backend y frontend.")
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
