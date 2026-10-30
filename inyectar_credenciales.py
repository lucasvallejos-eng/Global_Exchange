"""Módulo de automatización para descompresión, lectura, validación y sincronización de credenciales.

Gestiona:
  1. Descompresión automática de credenciales.zip (o credenciales.rar) en la raíz del proyecto.
  2. Parseo unificado de credenciales.txt (o text en su defecto).
  3. Validación estricta de formato, prefijos y rango de longitud para Stripe y Facturación Segura ESI.
  4. Modo interactivo por consola con bucle de reintento si las claves no existen o son inválidas.
  5. Inyección en los archivos .env del proyecto:
       - backend/.env.stripe
       - backend/.env.facturasegura
       - backend/.env
       - frontend/.env
       - .env (raíz)
       - .env.prod (si aplica en producción)
"""
import os
import re
import shutil
import subprocess
import sys
import zipfile
import getpass
import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

GOOGLE_DRIVE_FILE_ID = "16zYnoHtzSuXUMJud1I4GQCj_36pHHVO4"
GOOGLE_DRIVE_DOWNLOAD_URLS = (
    "https://drive.usercontent.google.com/download"
    f"?id={GOOGLE_DRIVE_FILE_ID}&export=download&confirm=t",
    "https://drive.google.com/uc"
    f"?export=download&id={GOOGLE_DRIVE_FILE_ID}&confirm=t",
)
# El ZIP local actualizado tiene prioridad sobre el RAR distribuido: permite
# conservar las credenciales renovables sin sobrescribir el archivo original.
ARCHIVOS_CREDENCIALES = ("credenciales.zip", "credenciales.rar")
NOMBRES_CREDENCIALES = ("credenciales.txt", "text", "credenciales.text")
PLACEHOLDERS = (
    "cambiar-por", "change-me", "placeholder", "tu-key", "your-key",
    "your-secret", "example.com", "reemplazar", "se solicita",
    "hay un error",
)

# =============================================================================
# 1. Descompresión y Localización de Archivos
# =============================================================================

def descomprimir_credenciales_zip(raiz: Path, log_fn=print) -> bool:
    """Verifica la existencia de 'credenciales.rar' (o 'credenciales.zip') en la raíz y lo descomprime.
    Emite una alerta en consola si no encuentra ningún archivo comprimido y continúa.
    """
    ruta_zip = raiz / "credenciales.zip"
    if ruta_zip.exists():
        log_fn(f"[credenciales] Archivo '{ruta_zip.name}' detectado en la raíz. Descomprimiendo en '{raiz}'...")
        try:
            with zipfile.ZipFile(ruta_zip, "r") as zf:
                zf.extractall(raiz)
            log_fn(f"[credenciales] Descompresión completada con éxito desde '{ruta_zip.name}'.")
            return True
        except Exception as e:
            log_fn(f"[credenciales] ALERTA: Error al descomprimir '{ruta_zip.name}': {e}.")
            return False

    ruta_rar = raiz / "credenciales.rar"
    if ruta_rar.exists():
        log_fn(f"[credenciales] Archivo '{ruta_rar.name}' detectado en la raíz. Descomprimiendo en '{raiz}'...")
        # Algunas copias se distribuyen como ZIP pero conservan la extensión .rar.
        # Detectar el formato por el contenido permite abrirlas sin 7-Zip/UnRAR.
        if zipfile.is_zipfile(ruta_rar):
            try:
                with zipfile.ZipFile(ruta_rar, "r") as zf:
                    zf.extractall(raiz)
                log_fn(f"[credenciales] El archivo '{ruta_rar.name}' contiene un ZIP; extracción completada.")
                return True
            except Exception as e:
                log_fn(f"[credenciales] ERROR al extraer el ZIP '{ruta_rar.name}': {e}.")
                return False
        # RAR no está soportado por las herramientas estándar de Python. Priorizar
        # 7-Zip/UnRAR. En Windows, usar el tar del sistema antes que el de Git Bash:
        # GNU tar interpreta una ruta C:\\... como un host remoto ("C:").
        extractor_7z = shutil.which("7z") or shutil.which("7zz")
        extractor_unrar = shutil.which("unrar")
        tar_sistema = Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "tar.exe"
        extractor_tar = (str(tar_sistema) if os.name == "nt" and tar_sistema.exists()
                         else shutil.which("tar"))
        if extractor_7z:
            comando = [extractor_7z, "x", "-y", f"-o{raiz}", str(ruta_rar)]
        elif extractor_unrar:
            comando = [extractor_unrar, "x", "-o+", str(ruta_rar), f"{raiz}{os.sep}"]
        elif extractor_tar:
            comando = [extractor_tar, "-xf", str(ruta_rar), "-C", str(raiz)]
        else:
            log_fn("[credenciales] ERROR: Para abrir credenciales.rar instalá 7-Zip y agregá 7z al PATH (o instalá UnRAR).")
            return False
        try:
            res = subprocess.run(comando, cwd=raiz, capture_output=True, text=True)
            if res.returncode == 0:
                log_fn(f"[credenciales] Descompresión completada con éxito desde '{ruta_rar.name}'.")
                return True
            detalle = (res.stderr or res.stdout or "sin detalle").strip()
            log_fn(f"[credenciales] ERROR al descomprimir '{ruta_rar.name}': {detalle}")
            return False
        except OSError as e:
            log_fn(f"[credenciales] ERROR al ejecutar el extractor para '{ruta_rar.name}': {e}.")
            return False

    log_fn("[credenciales] ALERTA: No se encontró 'credenciales.rar' ni 'credenciales.zip' en la raíz del proyecto. Continuando con modo interactivo...")
    return False


def descargar_credenciales(raiz: Path, log_fn=print) -> Path:
    """Garantiza un archivo local RAR/ZIP; el enlace público entrega RAR."""
    for nombre in ARCHIVOS_CREDENCIALES:
        archivo = raiz / nombre
        if not archivo.exists():
            continue
        if nombre.endswith(".zip") and not zipfile.is_zipfile(archivo):
            raise RuntimeError(
                "[CRITICAL ERROR] Error al descomprimir o extraer archivos desde "
                f"'{nombre}'. Abortando proceso."
            )
        return archivo

    destino = raiz / "credenciales.rar"
    log_fn("[credenciales] Descargando 'credenciales.rar' desde Google Drive...")
    temporal = destino.with_suffix(".rar.download")
    try:
        import urllib.request
        ultimo_error = None
        for url in GOOGLE_DRIVE_DOWNLOAD_URLS:
            try:
                solicitud = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Global-Exchange-credentials-bootstrap/1.0"},
                )
                with urllib.request.urlopen(solicitud, timeout=60) as respuesta, \
                        temporal.open("wb") as salida:
                    shutil.copyfileobj(respuesta, salida)
                firma = temporal.read_bytes()[:7]
                if firma.startswith(b"Rar!\x1a\x07") or zipfile.is_zipfile(temporal):
                    break
            except Exception as error:
                ultimo_error = error
        else:
            raise RuntimeError("No se pudo descargar desde Google Drive.") from ultimo_error
        if not temporal.exists() or temporal.stat().st_size == 0:
            raise RuntimeError("La descarga no produjo un archivo válido.")
        firma = temporal.read_bytes()[:7]
        if firma.startswith(b"Rar!\x1a\x07"):
            destino = raiz / "credenciales.rar"
        elif zipfile.is_zipfile(temporal):
            destino = raiz / "credenciales.zip"
        else:
            raise RuntimeError("La descarga no produjo un RAR o ZIP válido.")
        temporal.replace(destino)
        return destino
    except Exception as error:
        try:
            temporal.unlink(missing_ok=True)
        except OSError:
            pass
        raise RuntimeError(
            "[CRITICAL ERROR] No se detectó ni pudo descargarse 'credenciales.rar'. "
            "La ejecución se ha detenido. Sin este archivo el programa no puede "
            "correr adecuadamente."
        ) from error


def descargar_credenciales_zip(raiz: Path, log_fn=print) -> Path:
    """Compatibilidad: descarga el archivo de credenciales en formato RAR/ZIP."""
    return descargar_credenciales(raiz, log_fn=log_fn)


def extraer_credenciales(raiz: Path, log_fn=print) -> Path:
    """Extrae el RAR/ZIP en la raíz y devuelve el archivo de credenciales."""
    archivo = next(
        (raiz / nombre for nombre in ARCHIVOS_CREDENCIALES if (raiz / nombre).exists()),
        None,
    )
    if archivo is None:
        raise RuntimeError(
            "[CRITICAL ERROR] No se detectó ni pudo descargarse 'credenciales.rar'. "
            "La ejecución se ha detenido. Sin este archivo el programa no puede "
            "correr adecuadamente."
        )

    if archivo.suffix.lower() == ".rar" and not zipfile.is_zipfile(archivo):
        if not descomprimir_credenciales_zip(raiz, log_fn=log_fn):
            raise RuntimeError(
                "[CRITICAL ERROR] Error al descomprimir o extraer archivos desde "
                "'credenciales.rar'. Abortando proceso."
            )
        credenciales = buscar_archivo_credenciales(raiz)
        if credenciales is None:
            raise RuntimeError(
                "[CRITICAL ERROR] Error al descomprimir o extraer archivos desde "
                "'credenciales.rar'. Abortando proceso."
            )
        log_fn(f"[credenciales] Archivo interno detectado: '{credenciales}'.")
        return credenciales

    return extraer_credenciales_zip(raiz, log_fn=log_fn)


def extraer_credenciales_zip(raiz: Path, log_fn=print) -> Path:
    """Extrae un ZIP en la raíz y devuelve el archivo de credenciales."""
    archivo_zip = raiz / "credenciales.zip"
    try:
        with zipfile.ZipFile(archivo_zip) as zf:
            raiz_resuelta = raiz.resolve()
            miembros = zf.infolist()
            contiene_credenciales = any(
                Path(miembro.filename).name in NOMBRES_CREDENCIALES
                for miembro in miembros
                if not miembro.is_dir()
            )
            if not contiene_credenciales:
                raise ValueError("El ZIP no contiene un archivo de credenciales.")
            for miembro in miembros:
                destino = (raiz / miembro.filename).resolve()
                if destino != raiz_resuelta and raiz_resuelta not in destino.parents:
                    raise ValueError(f"Ruta de extracción inválida: {miembro.filename}")
            zf.extractall(raiz)
    except Exception as error:
        raise RuntimeError(
            "[CRITICAL ERROR] Error al descomprimir o extraer archivos desde "
            "'credenciales.zip'. Abortando proceso."
        ) from error

    archivo = buscar_archivo_credenciales(raiz)
    if archivo is None:
        raise RuntimeError(
            "[CRITICAL ERROR] Error al descomprimir o extraer archivos desde "
            "'credenciales.zip'. Abortando proceso."
        )
    log_fn(f"[credenciales] Archivo interno detectado: '{archivo}'.")
    return archivo


def _valor_real(valor):
    texto = str(valor or "").strip().lower()
    return bool(texto) and not any(marca in texto for marca in PLACEHOLDERS)


def preflight_credenciales_estricto(raiz: Path, log_fn=print) -> dict:
    """Descarga, extrae y valida credenciales sin permitir continuación parcial."""
    try:
        descargar_credenciales(raiz, log_fn=log_fn)
        extraer_credenciales(raiz, log_fn=log_fn)
        datos = obtener_y_validar_credenciales(raiz, log_fn=log_fn, interactivo=False)
        stripe = datos["stripe"]
        factura = datos["facturasegura"]

        obligatorias_stripe = ("STRIPE_PUBLIC_KEY", "STRIPE_SECRET_KEY")
        obligatorias_factura = (
            "FACTURA_SEGURA_URL",
            "FACTURA_SEGURA_EMISOR_RUC", "FACTURA_SEGURA_EMISOR_NOMBRE",
            "FACTURA_SEGURA_EMISOR_DIRECCION", "FACTURA_SEGURA_EMISOR_TELEFONO",
            "FACTURA_SEGURA_EMISOR_ACTIVIDAD_CODIGO", "FACTURA_SEGURA_EMISOR_ACTIVIDAD",
            "FACTURA_SEGURA_ESTABLECIMIENTO", "FACTURA_SEGURA_PUNTO_EXPEDICION",
        )
        faltantes = [
            clave for clave in obligatorias_stripe
            if not _valor_real(stripe.get(clave))
        ]
        faltantes += [
            clave for clave in obligatorias_factura
            if not _valor_real(factura.get(clave))
        ]
        if faltantes:
            raise ValueError("Variables obligatorias ausentes o con placeholders: " + ", ".join(faltantes))
        valido_url, motivo_url = validar_esi_facturacion_url(factura["FACTURA_SEGURA_URL"])
        if not valido_url:
            raise ValueError(motivo_url)
        valido_ruc, motivo_ruc = validar_esi_ruc(
            factura.get("ESI_RUC_EMISOR") or factura["FACTURA_SEGURA_EMISOR_RUC"]
        )
        if not valido_ruc:
            raise ValueError(motivo_ruc)
        log_fn("[credenciales] ZIP, extracción, parseo y validación completados.")
        return datos
    except Exception as error:
        if isinstance(error, RuntimeError) and str(error).startswith("[CRITICAL ERROR]"):
            raise
        raise RuntimeError(
            "[CRITICAL ERROR] Error durante el parseo de credenciales de Stripe / "
            "Facturación Segura ESI. Abortando ejecucion."
        ) from error


def buscar_archivo_credenciales(raiz: Path) -> Path | None:
    """Busca credenciales.txt o text (o credenciales.text) en la raíz del proyecto.

    Prioridad:
      1. credenciales.txt
      2. text
      3. credenciales.text
    """
    for nombre in ("credenciales.txt", "text", "credenciales.text"):
        ruta = raiz / nombre
        if ruta.exists():
            return ruta
    # El RAR distribuido guarda el archivo bajo credenciales/credenciales/.
    # Buscar en subdirectorios permite usar esa estructura sin mover el archivo.
    for nombre in ("credenciales.txt", "text", "credenciales.text"):
        coincidencias = sorted(raiz.glob(f"**/{nombre}"))
        if coincidencias:
            return coincidencias[0]
    return None


# =============================================================================
# 2. Funciones de Validación de Claves (Prefijos y Rango de Longitud)
# =============================================================================

def validar_stripe_public_key(clave: str) -> tuple[bool, str]:
    """Valida la clave pública de Stripe (Publishable Key).

    Requisitos:
      - Prefijo 'pk_test_' (modo test) o 'pk_live_' (modo live).
      - Longitud entre 30 y 150 caracteres.
      - Caracteres alfanuméricos tras el prefijo.
    """
    clave = (clave or "").strip()
    if not clave:
        return False, "La clave pública de Stripe no puede estar vacía"
    if not (clave.startswith("pk_test_") or clave.startswith("pk_live_")):
        return False, "Debe comenzar con el prefijo 'pk_test_' (o 'pk_live_')"
    if not (30 <= len(clave) <= 150):
        return False, f"Longitud fuera de rango ({len(clave)} caracteres). Debe tener entre 30 y 150 caracteres"
    if not re.match(r"^pk_(?:test|live)_[A-Za-z0-9_]+$", clave):
        return False, "Contiene caracteres inválidos; solo se admiten caracteres alfanuméricos y guiones bajos"
    return True, ""


def validar_stripe_secret_key(clave: str) -> tuple[bool, str]:
    """Valida la clave secreta de Stripe (Secret Key).

    Requisitos:
      - Prefijo 'sk_test_' (modo test) o 'sk_live_' (modo live).
      - Longitud entre 30 y 150 caracteres.
      - Caracteres alfanuméricos tras el prefijo.
    """
    clave = (clave or "").strip()
    if not clave:
        return False, "La clave secreta de Stripe no puede estar vacía"
    if not (clave.startswith("sk_test_") or clave.startswith("sk_live_")):
        return False, "Debe comenzar con el prefijo 'sk_test_' (o 'sk_live_')"
    if not (30 <= len(clave) <= 150):
        return False, f"Longitud fuera de rango ({len(clave)} caracteres). Debe tener entre 30 y 150 caracteres"
    if not re.match(r"^sk_(?:test|live)_[A-Za-z0-9_]+$", clave):
        return False, "Contiene caracteres inválidos; solo se admiten caracteres alfanuméricos y guiones bajos"
    return True, ""


def validar_esi_facturacion_key(clave: str) -> tuple[bool, str]:
    """Valida la clave / token de Facturación Segura ESI.

    Requisitos:
      - Prefijo 'esi_' (ej. esi_live_ o esi_test_), formato UUID, JWT, o token
        alfanumérico seguro de 16 a 150 caracteres.
      - Longitud entre 16 y 150 caracteres.
    """
    clave = (clave or "").strip()
    if not clave:
        return False, "El API Key / Token de Facturación Segura ESI no puede estar vacío"

    es_uuid = bool(re.match(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", clave))
    es_esi = clave.startswith("esi_")
    es_jwt = bool(re.match(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$", clave))
    es_token_valido = bool(re.match(r"^[A-Za-z0-9_\-]+$", clave)) and (16 <= len(clave) <= 150)

    if not (es_uuid or es_esi or es_jwt or es_token_valido):
        return False, "Debe tener prefijo 'esi_' (ej. esi_test_...), ser un UUID, JWT o una clave alfanumérica válida"
    if not (16 <= len(clave) <= 150):
        return False, f"Longitud fuera de rango ({len(clave)} caracteres). Debe tener entre 16 y 150 caracteres"
    return True, ""


def validar_esi_facturacion_url(url: str) -> tuple[bool, str]:
    """Valida la URL del servicio de Facturación Segura ESI."""
    url = (url or "").strip()
    if not url:
        return False, "La URL de Facturación Segura no puede estar vacía"
    if not (url.startswith("http://") or url.startswith("https://")):
        return False, "La URL debe comenzar con http:// o https://"
    return True, ""


def validar_esi_ruc(ruc: str) -> tuple[bool, str]:
    """Valida el RUC del emisor (ej. 2595733-3 o 80012345-6)."""
    ruc = (ruc or "").strip()
    if not ruc:
        return False, "El RUC del emisor no puede estar vacío"
    if not re.match(r"^\d{5,9}(-\d)?$", ruc):
        return False, "Formato de RUC inválido (ej. 80012345-6 o 2595733-3)"
    return True, ""


# =============================================================================
# 3. Parseo Unificado de Credenciales
# =============================================================================

def parsear_credenciales(ruta_archivo: Path) -> dict:
    """Lee y parsea un archivo de credenciales (credenciales.txt o text).

    Extrae bloques de configuración:
      - [CONFIGURACIÓN PARA VARIABLES DE ENTORNO (backend/.env.stripe)]
      - [CONFIGURACIÓN PARA VARIABLES DE ENTORNO (backend/.env.facturasegura)]
      - Pares clave=valor generales
      - Metadatos descriptivos (Identificador / Token, Endpoint API, RUC Completo)

    Retorna un diccionario con:
      - 'stripe': variables de Stripe
      - 'facturasegura': variables de Facturación Segura ESI
      - 'todas': diccionario consolidado
      - 'archivo': ruta del archivo parseado
    """
    resultado = {
        "stripe": {},
        "facturasegura": {},
        "todas": {},
        "archivo": str(ruta_archivo) if ruta_archivo else None,
    }

    if not ruta_archivo or not ruta_archivo.exists():
        return resultado

    lineas = ruta_archivo.read_text(encoding="utf-8", errors="replace").splitlines()
    seccion_actual = "general"

    for linea in lineas:
        linea_strip = linea.strip()
        if not linea_strip:
            continue

        # Detectar encabezados de bloque tipo [ ... ]
        if linea_strip.startswith("[") and linea_strip.endswith("]"):
            header_lower = linea_strip.lower()
            if "stripe" in header_lower:
                seccion_actual = "stripe"
            elif "factura" in header_lower or "esi" in header_lower:
                seccion_actual = "facturasegura"
            else:
                seccion_actual = "general"
            continue

        # Parsear líneas de metadatos descriptivos con viñeta '-'
        if linea_strip.startswith("-"):
            linea_lower = linea_strip.lower()
            if "identificador / token:" in linea_lower:
                val = linea_strip.split(":", 1)[1].strip()
                if val:
                    resultado["facturasegura"].setdefault("FACTURA_SEGURA_TOKEN", val)
                    resultado["facturasegura"].setdefault("ESI_FACTURACION_API_KEY", val)
            elif "endpoint api:" in linea_lower:
                val = linea_strip.split(":", 1)[1].strip()
                if val:
                    resultado["facturasegura"].setdefault("FACTURA_SEGURA_URL", val)
                    resultado["facturasegura"].setdefault("ESI_FACTURACION_URL", val)
            elif "ruc completo:" in linea_lower:
                val = linea_strip.split(":", 1)[1].strip()
                if val:
                    resultado["facturasegura"].setdefault("ESI_RUC_EMISOR", val)
            elif "clave pública" in linea_lower:
                val = linea_strip.split(":", 1)[1].strip()
                if val:
                    resultado["stripe"].setdefault("STRIPE_PUBLIC_KEY", val)
                    resultado["stripe"].setdefault("STRIPE_PUBLISHABLE_KEY", val)
            elif "clave secreta" in linea_lower:
                val = linea_strip.split(":", 1)[1].strip()
                if val:
                    resultado["stripe"].setdefault("STRIPE_SECRET_KEY", val)
            continue

        # Parsear líneas con formato CLAVE=VALOR
        if "=" in linea_strip:
            clave, valor = linea_strip.split("=", 1)
            clave = clave.strip()
            valor = valor.strip()

            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", clave):
                continue

            if seccion_actual == "stripe" or clave.startswith("STRIPE_") or clave.startswith("VITE_STRIPE"):
                if valor:
                    resultado["stripe"][clave] = valor
            elif seccion_actual == "facturasegura" or clave.startswith("FACTURA_") or clave.startswith("FACTURASEGURA_") or clave.startswith("ESI_"):
                if valor:
                    resultado["facturasegura"][clave] = valor

            if valor:
                resultado["todas"][clave] = valor

    # Normalización de variables de Stripe
    stripe = resultado["stripe"]
    pub_key = stripe.get("STRIPE_PUBLIC_KEY") or stripe.get("STRIPE_PUBLISHABLE_KEY") or stripe.get("VITE_STRIPE_PUBLISHABLE_KEY")
    if pub_key:
        stripe["STRIPE_PUBLIC_KEY"] = pub_key
        stripe["STRIPE_PUBLISHABLE_KEY"] = pub_key
        stripe["VITE_STRIPE_PUBLISHABLE_KEY"] = pub_key

    # Normalización de variables de Facturación Segura ESI
    factura = resultado["facturasegura"]
    token = factura.get("ESI_FACTURACION_API_KEY") or factura.get("FACTURA_SEGURA_TOKEN") or factura.get("FACTURASEGURA_API_KEY") or factura.get("FACTURASEGURA_SECRET")
    if token:
        factura["ESI_FACTURACION_API_KEY"] = token
        factura["FACTURA_SEGURA_TOKEN"] = token
        factura.setdefault("FACTURASEGURA_API_KEY", token)
        factura.setdefault("FACTURASEGURA_SECRET", token)

    url = factura.get("ESI_FACTURACION_URL") or factura.get("FACTURA_SEGURA_URL") or factura.get("FACTURASEGURA_URL")
    if url:
        factura["ESI_FACTURACION_URL"] = url
        factura["FACTURA_SEGURA_URL"] = url
        factura["FACTURASEGURA_URL"] = url

    ruc_emisor = (
        factura.get("ESI_RUC_EMISOR")
        or factura.get("FACTURA_SEGURA_EMISOR_RUC")
        or factura.get("FACTURASEGURA_EMISOR_RUC")
    )
    if ruc_emisor:
        factura["ESI_RUC_EMISOR"] = ruc_emisor
        if "-" in ruc_emisor:
            ruc_sin_dv, dv = ruc_emisor.split("-", 1)
            factura["FACTURA_SEGURA_EMISOR_RUC"] = ruc_sin_dv
            factura["FACTURA_SEGURA_EMISOR_DV"] = dv
        else:
            factura["FACTURA_SEGURA_EMISOR_RUC"] = ruc_emisor

    # Aceptar la nomenclatura FACTURASEGURA_* solicitada por los archivos
    # externos y normalizarla al contrato interno del backend.
    for sufijo in (
        "EMISOR_NOMBRE", "EMISOR_DIRECCION", "EMISOR_TELEFONO",
        "EMISOR_ACTIVIDAD_CODIGO", "EMISOR_ACTIVIDAD",
        "EMISOR_ESTABLECIMIENTO", "EMISOR_PUNTO_EXPEDICION",
    ):
        valor = (
            factura.get(f"FACTURA_SEGURA_{sufijo}")
            or factura.get(f"FACTURASEGURA_{sufijo}")
            or factura.get(f"ESI_{sufijo}")
        )
        if valor:
            factura[f"FACTURA_SEGURA_{sufijo}"] = valor
    for clave, alias in (
        ("FACTURA_SEGURA_URL", "FACTURASEGURA_URL"),
        ("FACTURA_SEGURA_TOKEN", "FACTURASEGURA_API_KEY"),
        ("FACTURA_SEGURA_TOKEN", "FACTURASEGURA_SECRET"),
    ):
        if not factura.get(clave) and factura.get(alias):
            factura[clave] = factura[alias]
    if factura.get("FACTURA_SEGURA_EMISOR_ESTABLECIMIENTO"):
        factura["FACTURA_SEGURA_ESTABLECIMIENTO"] = factura[
            "FACTURA_SEGURA_EMISOR_ESTABLECIMIENTO"
        ]
    if factura.get("FACTURA_SEGURA_EMISOR_PUNTO_EXPEDICION"):
        factura["FACTURA_SEGURA_PUNTO_EXPEDICION"] = factura[
            "FACTURA_SEGURA_EMISOR_PUNTO_EXPEDICION"
        ]

    return resultado


# =============================================================================
# 4. Modo Interactivo con Validación en Bucle
# =============================================================================

def pedir_interactivo(
    nombre_var: str,
    validador_fn,
    descripcion: str = "",
    valor_defecto: str = "",
    log_fn=print
) -> str:
    """Solicita interactivamente el ingreso de una clave por consola con validación en bucle."""
    aviso_def = f" [Por defecto: {valor_defecto}]" if valor_defecto else ""
    desc_str = f" ({descripcion})" if descripcion else ""
    prompt = f"\n[credenciales] Ingrese '{nombre_var}'{desc_str}{aviso_def}: "

    while True:
        try:
            entrada = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            log_fn("\n[credenciales] Operación cancelada por el usuario.")
            raise

        if not entrada and valor_defecto:
            entrada = valor_defecto

        valido, motivo = validador_fn(entrada)
        if valido:
            log_fn(f"[credenciales] '{nombre_var}' validado exitosamente.")
            return entrada
        log_fn(f"[credenciales] [ERROR] Valor no válido: {motivo}. Por favor, intente de nuevo.")


def token_esi_existente(raiz: Path) -> str:
    """Conserva el token de sesión renovado en el entorno local."""
    candidatos = (
        raiz / "backend" / ".env.facturasegura",
        raiz / "backend" / ".env",
        raiz / ".env",
    )
    claves_token = {
        "FACTURA_SEGURA_TOKEN",
        "ESI_FACTURACION_API_KEY",
        "FACTURASEGURA_API_KEY",
        "FACTURASEGURA_SECRET",
    }
    for ruta in candidatos:
        if not ruta.exists():
            continue
        for linea in ruta.read_text(encoding="utf-8", errors="replace").splitlines():
            texto = linea.strip()
            if not texto or texto.startswith("#") or "=" not in texto:
                continue
            clave, valor = (parte.strip() for parte in texto.split("=", 1))
            if clave not in claves_token:
                continue
            valido, _ = validar_esi_facturacion_key(valor)
            if valido and len(valor) > 36:
                return valor
    return ""


def obtener_y_validar_credenciales(raiz: Path, log_fn=print, interactivo: bool = True) -> dict:
    """Obtiene y valida exhaustivamente las claves de Stripe y Facturación Segura ESI.

    Si no se encuentran los archivos o las claves son inválidas, solicita el ingreso
    interactivo por consola con validación en bucle.
    """
    archivo = buscar_archivo_credenciales(raiz)
    if archivo:
        log_fn(f"[credenciales] Archivo de credenciales detectado: '{archivo.name}'. Parseando...")
        datos = parsear_credenciales(archivo)
    else:
        log_fn("[credenciales] Aviso: No se detectó 'credenciales.txt' ni 'text'. Se solicitarán las claves interactivamente.")
        datos = {"stripe": {}, "facturasegura": {}, "todas": {}, "archivo": None}

    stripe = datos["stripe"]
    factura = datos["facturasegura"]

    # 1. Validar STRIPE_PUBLIC_KEY
    stripe_pub = stripe.get("STRIPE_PUBLIC_KEY") or stripe.get("STRIPE_PUBLISHABLE_KEY") or ""
    valido_pub, motivo_pub = validar_stripe_public_key(stripe_pub)
    if not valido_pub:
        log_fn(f"[credenciales] STRIPE_PUBLIC_KEY ausente o inválida ({motivo_pub}).")
        if interactivo:
            stripe_pub = pedir_interactivo(
                "STRIPE_PUBLIC_KEY",
                validar_stripe_public_key,
                "Clave pública de Stripe, ej. pk_test_...",
                log_fn=log_fn
            )
        else:
            raise ValueError(f"STRIPE_PUBLIC_KEY inválida: {motivo_pub}")
    else:
        log_fn(f"[credenciales] STRIPE_PUBLIC_KEY validada: {stripe_pub[:12]}...{stripe_pub[-4:]}")

    # 2. Validar STRIPE_SECRET_KEY
    stripe_sec = stripe.get("STRIPE_SECRET_KEY", "")
    valido_sec, motivo_sec = validar_stripe_secret_key(stripe_sec)
    if not valido_sec:
        log_fn(f"[credenciales] STRIPE_SECRET_KEY ausente o inválida ({motivo_sec}).")
        if interactivo:
            stripe_sec = pedir_interactivo(
                "STRIPE_SECRET_KEY",
                validar_stripe_secret_key,
                "Clave secreta de Stripe, ej. sk_test_...",
                log_fn=log_fn
            )
        else:
            raise ValueError(f"STRIPE_SECRET_KEY inválida: {motivo_sec}")
    else:
        log_fn(f"[credenciales] STRIPE_SECRET_KEY validada: {stripe_sec[:12]}...{stripe_sec[-4:]}")

    # 3. Validar ESI_FACTURACION_API_KEY / FACTURA_SEGURA_TOKEN
    factura_token = (
        factura.get("ESI_FACTURACION_API_KEY")
        or factura.get("FACTURA_SEGURA_TOKEN")
        or factura.get("FACTURASEGURA_API_KEY")
        or ""
    )
    token_existente = token_esi_existente(raiz)
    if token_existente and len(token_existente) > len(factura_token):
        factura_token = token_existente
        log_fn(
            "[credenciales] Conservando el token ESI renovado del entorno local "
            f"(longitud: {len(token_existente)})."
        )
    valido_tok, motivo_tok = validar_esi_facturacion_key(factura_token)
    if not valido_tok:
        log_fn(f"[credenciales] Facturación Segura ESI API Key / Token ausente o inválido ({motivo_tok}).")
        if interactivo:
            factura_token = pedir_interactivo(
                "ESI_FACTURACION_API_KEY",
                validar_esi_facturacion_key,
                "Token de Facturación Segura ESI, ej. esi_test_... o UUID",
                valor_defecto="",
                log_fn=log_fn
            )
        else:
            factura_token = ""
    else:
        log_fn(f"[credenciales] Facturación Segura ESI API Key validada: {factura_token[:8]}...{factura_token[-4:]}")

    # 4. Validar URL y RUC de Facturación Segura
    factura_url = factura.get("ESI_FACTURACION_URL") or factura.get("FACTURA_SEGURA_URL") or "https://apitest.facturasegura.com.py"
    factura_ruc = factura.get("ESI_RUC_EMISOR") or factura.get("FACTURA_SEGURA_EMISOR_RUC") or "2595733-3"

    # Actualizar diccionarios normalizados
    stripe["STRIPE_PUBLIC_KEY"] = stripe_pub
    stripe["STRIPE_PUBLISHABLE_KEY"] = stripe_pub
    stripe["VITE_STRIPE_PUBLISHABLE_KEY"] = stripe_pub
    stripe["STRIPE_SECRET_KEY"] = stripe_sec

    factura["ESI_FACTURACION_API_KEY"] = factura_token
    factura["FACTURA_SEGURA_TOKEN"] = factura_token
    factura["FACTURASEGURA_API_KEY"] = factura_token
    factura["FACTURASEGURA_SECRET"] = factura_token
    factura["ESI_FACTURACION_URL"] = factura_url
    factura["FACTURA_SEGURA_URL"] = factura_url
    factura["FACTURASEGURA_URL"] = factura_url
    factura["ESI_RUC_EMISOR"] = factura_ruc
    if "-" in factura_ruc:
        r, d = factura_ruc.split("-", 1)
        factura["FACTURA_SEGURA_EMISOR_RUC"] = r
        factura["FACTURA_SEGURA_EMISOR_DV"] = d
    else:
        factura["FACTURA_SEGURA_EMISOR_RUC"] = factura_ruc

    datos["stripe"] = stripe
    datos["facturasegura"] = factura
    datos["todas"].update(stripe)
    datos["todas"].update(factura)
    return datos


def actualizar_token_esi(raiz: Path, log_fn=print) -> str:
    """Obtiene un token TEST nuevo y lo sincroniza en los entornos locales.

    El correo puede venir de FACTURA_SEGURA_LOGIN_EMAIL o del emisor. La
    contraseña se lee de FACTURA_SEGURA_LOGIN_PASSWORD o se solicita sin
    mostrarla en pantalla; nunca se escribe en el repositorio.
    """
    env_path = raiz / "backend" / ".env.facturasegura"
    valores = {}
    if env_path.exists():
        for linea in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" in linea and not linea.lstrip().startswith("#"):
                clave, valor = linea.split("=", 1)
                valores[clave.strip()] = valor.strip()

    correo = (
        os.environ.get("FACTURA_SEGURA_LOGIN_EMAIL")
        or valores.get("FACTURA_SEGURA_LOGIN_EMAIL")
        or valores.get("FACTURA_SEGURA_EMISOR_EMAIL")
        or "gamarrag446@fpuna.edu.py"
    )
    contrasena = (
        os.environ.get("FACTURA_SEGURA_LOGIN_PASSWORD")
        or valores.get("FACTURA_SEGURA_LOGIN_PASSWORD")
    )
    if not contrasena:
        if not sys.stdin.isatty():
            raise RuntimeError(
                "No se definió FACTURA_SEGURA_LOGIN_PASSWORD. "
                "Configúrala como variable de entorno para obtener el token TEST."
            )
        contrasena = getpass.getpass(
            f"[credenciales] Contraseña TEST de Factura Segura para {correo}: "
        )

    url = (valores.get("FACTURA_SEGURA_URL") or "https://apitest.facturasegura.com.py").rstrip("/")
    if url.endswith("/misife00/v1/esi"):
        url = url[:-len("/misife00/v1/esi")].rstrip("/")
    login_url = f"{url}/login?include_auth_token"
    solicitud = urllib.request.Request(
        login_url,
        data=urllib.parse.urlencode({"email": correo, "password": contrasena}).encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(solicitud, timeout=30) as respuesta:
            cuerpo = json.load(respuesta)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"Login de Factura Segura rechazado (HTTP {error.code}).") from error
    except (OSError, ValueError) as error:
        raise RuntimeError("No se pudo obtener el token TEST de Factura Segura.") from error

    try:
        token = cuerpo["response"]["user"]["authentication_token"]
    except (KeyError, TypeError) as error:
        raise RuntimeError("La respuesta de Factura Segura no contiene authentication_token.") from error
    valido, motivo = validar_esi_facturacion_key(token)
    if not valido or len(token) <= 36:
        raise RuntimeError(f"Factura Segura devolvió un token inválido: {motivo}")

    cambios = {
        "FACTURA_SEGURA_TOKEN": token,
        "FACTURASEGURA_API_KEY": token,
        "FACTURASEGURA_SECRET": token,
        "ESI_FACTURACION_API_KEY": token,
    }
    for destino in (
        raiz / "backend" / ".env.facturasegura",
        raiz / "backend" / ".env",
        raiz / ".env",
    ):
        actualizar_o_crear_archivo_env(destino, None, cambios)
    prod = raiz / ".env.prod"
    if prod.exists():
        actualizar_o_crear_archivo_env(prod, None, cambios)
    log_fn(f"[credenciales] Token TEST de Factura Segura actualizado (longitud: {len(token)}).")
    return token


# =============================================================================
# 5. Inyección en Archivos .env
# =============================================================================

def actualizar_o_crear_archivo_env(path_env: Path, path_example: Path | None, cambios: dict):
    """Actualiza o crea un archivo .env reemplazando o agregando variables
    sin perder comentarios existentes."""
    if not path_env.exists():
        if path_example and path_example.exists():
            shutil.copy(path_example, path_env)
        else:
            path_env.parent.mkdir(parents=True, exist_ok=True)
            path_env.touch()

    lineas = path_env.read_text(encoding="utf-8", errors="replace").splitlines() if path_env.exists() else []
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


def inyectar_credenciales(
    raiz: Path = None,
    log_fn=print,
    archivo_prod: Path | None = None,
    datos_validados: dict | None = None,
    interactivo: bool = True,
    renovar_token_esi: bool = False,
) -> bool:
    """Inyecta las credenciales validadas de Stripe y Facturación Segura ESI en:
      - backend/.env.stripe
      - backend/.env.facturasegura
      - backend/.env
      - frontend/.env
      - .env (raíz)
      - archivo_prod (si aplica)

    Con ``renovar_token_esi=True``, al finalizar inicia sesión en Factura
    Segura TEST y reemplaza cualquier marcador o token vencido. La contraseña
    se toma de FACTURA_SEGURA_LOGIN_PASSWORD o se solicita sin mostrarla.
    """
    if raiz is None:
        raiz = Path(__file__).resolve().parent

    if datos_validados is None:
        descomprimir_credenciales_zip(raiz, log_fn=log_fn)
        datos_validados = obtener_y_validar_credenciales(raiz, log_fn=log_fn, interactivo=interactivo)

    stripe_vars = datos_validados.get("stripe", {})
    factura_vars = datos_validados.get("facturasegura", {})

    backend_dir = raiz / "backend"
    frontend_dir = raiz / "frontend"

    # 1. backend/.env.stripe
    if stripe_vars:
        stripe_backend_cambios = {
            "STRIPE_PUBLISHABLE_KEY": stripe_vars.get("STRIPE_PUBLISHABLE_KEY", ""),
            "STRIPE_SECRET_KEY": stripe_vars.get("STRIPE_SECRET_KEY", ""),
            "STRIPE_PUBLIC_KEY": stripe_vars.get("STRIPE_PUBLIC_KEY", ""),
        }
        actualizar_o_crear_archivo_env(
            backend_dir / ".env.stripe",
            backend_dir / ".env.stripe.example",
            stripe_backend_cambios
        )

    # 2. backend/.env.facturasegura
    if factura_vars:
        actualizar_o_crear_archivo_env(
            backend_dir / ".env.facturasegura",
            backend_dir / ".env.facturasegura.example",
            factura_vars
        )

    # 3. backend/.env (consolidado)
    cambios_backend_env = {}
    cambios_backend_env.update(stripe_vars)
    cambios_backend_env.update(factura_vars)
    if cambios_backend_env:
        actualizar_o_crear_archivo_env(
            backend_dir / ".env",
            backend_dir / ".env.example",
            cambios_backend_env
        )

    # 4. frontend/.env
    cambios_frontend = {}
    if "VITE_STRIPE_PUBLISHABLE_KEY" in stripe_vars:
        cambios_frontend["VITE_STRIPE_PUBLISHABLE_KEY"] = stripe_vars["VITE_STRIPE_PUBLISHABLE_KEY"]
    if "STRIPE_PUBLISHABLE_KEY" in stripe_vars:
        cambios_frontend["STRIPE_PUBLISHABLE_KEY"] = stripe_vars["STRIPE_PUBLISHABLE_KEY"]
    if "STRIPE_PUBLIC_KEY" in stripe_vars:
        cambios_frontend["STRIPE_PUBLIC_KEY"] = stripe_vars["STRIPE_PUBLIC_KEY"]
    if cambios_frontend:
        frontend_example = frontend_dir / ".env.example" if (frontend_dir / ".env.example").exists() else raiz / ".env.example"
        actualizar_o_crear_archivo_env(
            frontend_dir / ".env",
            frontend_example,
            cambios_frontend
        )

    # 5. .env de la raíz
    cambios_raiz = {}
    cambios_raiz.update(stripe_vars)
    cambios_raiz.update(factura_vars)
    if cambios_raiz:
        actualizar_o_crear_archivo_env(
            raiz / ".env",
            raiz / ".env.example",
            cambios_raiz
        )

    # 6. .env.prod (si aplica en producción)
    if archivo_prod and archivo_prod.exists():
        prod_cambios = {}
        if "STRIPE_PUBLISHABLE_KEY" in stripe_vars:
            prod_cambios["STRIPE_PUBLISHABLE_KEY"] = stripe_vars["STRIPE_PUBLISHABLE_KEY"]
        if "STRIPE_SECRET_KEY" in stripe_vars:
            prod_cambios["STRIPE_SECRET_KEY"] = stripe_vars["STRIPE_SECRET_KEY"]
        if prod_cambios:
            actualizar_o_crear_archivo_env(
                archivo_prod,
                raiz / ".env.prod.example",
                prod_cambios
            )

    origen = datos_validados.get("archivo") or "ingreso interactivo"
    log_fn(f"[credenciales] Credenciales inyectadas exitosamente en backend/.env, frontend/.env y .env (origen: {origen}).")
    if renovar_token_esi:
        actualizar_token_esi(raiz, log_fn=log_fn)
    return True


if __name__ == "__main__":
    raiz_actual = Path(__file__).resolve().parent
    descomprimir_credenciales_zip(raiz_actual, log_fn=print)
    datos_ok = obtener_y_validar_credenciales(raiz_actual, log_fn=print, interactivo=True)
    inyectar_credenciales(
        raiz_actual,
        log_fn=print,
        archivo_prod=raiz_actual / ".env.prod",
        datos_validados=datos_ok
    )
