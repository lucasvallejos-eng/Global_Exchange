"""Despliegue automático de Global Exchange, en desarrollo o en producción.

Un solo comando deja el sistema funcionando:

  1. Código fuente: baja del repositorio la versión pedida (un tag de release).
  2. Base de datos: la crea con las migraciones; con --base-nueva, desde cero.
  3. Población: carga los datos de ejemplo y crea un usuario por rol.

Uso, con Docker Desktop abierto:

    python desplegar.py --ambiente desarrollo
    python desplegar.py --ambiente produccion --tag v5.0
    python desplegar.py --ambiente desarrollo --base-nueva

Se puede correr dentro del repositorio ya clonado o suelto en una carpeta
vacía: ahí clona el repositorio en ./Global_Exchange y sigue.

El trabajo de cada ambiente lo hacen los scripts que ya existían:
levantar_todo.py (desarrollo) y publicar.py (producción, en internet).

Requisitos: Git, Python 3.12+, Docker y, para desarrollo, Node.js 20+.
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPOSITORIO = "https://github.com/lucasvallejos-eng/Global_Exchange.git"
AQUI = Path(__file__).resolve().parent
ES_WINDOWS = os.name == "nt"

for flujo in (sys.stdout, sys.stderr):
    try:
        flujo.reconfigure(errors="replace")
    except AttributeError:
        pass


def log(mensaje):
    print(f"[desplegar] {mensaje}", flush=True)


def git(*args, cwd, capturar=False):
    return subprocess.run(["git", *args], cwd=cwd, text=True, encoding="utf-8",
                          errors="replace", capture_output=capturar)


def revisar_requisitos(ambiente):
    necesarios = ["git", "docker"] + (["node"] if ambiente == "desarrollo" else [])
    faltan = [programa for programa in necesarios if not shutil.which(programa)]
    if faltan:
        sys.exit(f"[desplegar] Falta instalar: {', '.join(faltan)}.")
    if subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
        sys.exit("[desplegar] Docker no responde. Abrí Docker Desktop y probá de nuevo.")


def codigo_fuente(tag):
    """Deja el código en la versión pedida y devuelve la carpeta del repositorio.

    Sin ``tag`` se usa lo que haya: lo recién clonado (la rama principal, que
    es el último release) o lo que esté en la carpeta si ya era un clon.
    """
    raiz = AQUI if (AQUI / ".git").exists() else AQUI / "Global_Exchange"
    if not (raiz / ".git").exists():
        log(f"Clonando {REPOSITORIO} en {raiz} ...")
        if git("clone", REPOSITORIO, str(raiz), cwd=AQUI).returncode != 0:
            sys.exit("[desplegar] No se pudo clonar el repositorio.")
    if tag:
        # Cambiar de versión pisa los archivos: primero, que no haya trabajo sin guardar.
        if git("status", "--porcelain", "--untracked-files=no", cwd=raiz, capturar=True).stdout.strip():
            sys.exit("[desplegar] Hay cambios sin commitear en el repositorio. "
                     "Guardalos o descartalos antes de cambiar de versión.")
        git("fetch", "--tags", "origin", cwd=raiz, capturar=True)
        if git("checkout", "--detach", tag, cwd=raiz, capturar=True).returncode != 0:
            sys.exit(f"[desplegar] No existe la versión {tag}. Las que hay: "
                     + ", ".join(git("tag", "-l", cwd=raiz, capturar=True).stdout.split()))
    version = git("describe", "--tags", "--always", cwd=raiz, capturar=True).stdout.strip()
    log(f"Código fuente: versión {version}, en {raiz}")
    return raiz


def borrar_base(raiz, ambiente):
    """--base-nueva: borra los datos para que el despliegue arranque de cero."""
    if ambiente == "desarrollo":
        # La base de Keycloak de desarrollo la recrea siempre levantar_todo.py.
        base = Path(os.environ.get("DJANGO_DB_PATH") or raiz / "backend" / "db.sqlite3")
        base.unlink(missing_ok=True)
        log(f"Base de datos borrada: {base}")
    elif (raiz / ".env.prod").exists():
        # Borra los volúmenes (Django y Keycloak). Las claves de .env.prod se
        # conservan, así la base nueva de Keycloak se crea con la misma.
        log("Borrando el ambiente de producción y sus datos (docker compose down -v)...")
        subprocess.run(["docker", "compose", "-f", "docker-compose.prod.yml",
                        "-f", "docker-compose.publico.yml", "--env-file", ".env.prod",
                        "down", "-v"], cwd=raiz, check=True)


def python_del_proyecto(raiz):
    """El Python del entorno virtual del backend, con sus dependencias
    (publicar.py las necesita). Lo crea si no existe."""
    entorno = raiz / "backend" / ".venv"
    python = entorno / ("Scripts/python.exe" if ES_WINDOWS else "bin/python")
    if not python.exists():
        log("Creando el entorno virtual del backend...")
        subprocess.run([sys.executable, "-m", "venv", str(entorno)], check=True)
    subprocess.run([str(python), "-m", "pip", "install", "-q", "-r",
                    str(raiz / "backend" / "requirements.txt")], check=True)
    return str(python)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ambiente", required=True, choices=["desarrollo", "produccion"])
    parser.add_argument("--tag", help="versión a desplegar (por ejemplo v5.0); por defecto, la que esté")
    parser.add_argument("--base-nueva", action="store_true",
                        help="borra los datos que haya y crea la base de cero")
    parser.add_argument("--sin-datos", action="store_true",
                        help="producción: no cargar los datos de ejemplo ni los usuarios de prueba")
    args = parser.parse_args()

    revisar_requisitos(args.ambiente)
    raiz = codigo_fuente(args.tag)
    if args.base_nueva:
        borrar_base(raiz, args.ambiente)

    # Las migraciones (base de datos) y la carga de datos (población) las
    # corre el script de cada ambiente.
    if args.ambiente == "desarrollo":
        if args.sin_datos:
            log("Aviso: en desarrollo los datos de ejemplo se cargan siempre (lo hace levantar_todo.py).")
        comando = [sys.executable, "levantar_todo.py"]
    else:
        comando = [python_del_proyecto(raiz), "publicar.py"] + ([] if args.sin_datos else ["--demo"])
    log(f"Desplegando en {args.ambiente}...")
    try:
        return subprocess.run(comando, cwd=raiz).returncode
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
