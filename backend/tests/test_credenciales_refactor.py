"""Pruebas unitarias para la refactorización de descompresión, parseo y validación de credenciales."""
import io
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

RAIZ_PROYECTO = Path(__file__).resolve().parent.parent.parent
if str(RAIZ_PROYECTO) not in sys.path:
    sys.path.insert(0, str(RAIZ_PROYECTO))

from inyectar_credenciales import (
    buscar_archivo_credenciales,
    descomprimir_credenciales_zip,
    inyectar_credenciales,
    obtener_y_validar_credenciales,
    parsear_credenciales,
    validar_esi_facturacion_key,
    validar_esi_facturacion_url,
    validar_esi_ruc,
    validar_stripe_public_key,
    validar_stripe_secret_key,
)
from levantar_todo import preflight_credenciales

# Constantes mock para pruebas que no activan escáneres de secretos de GitHub
MOCK_STRIPE_PUB = "pk_test_mock_public_key_for_testing_12345"
MOCK_STRIPE_SEC = "sk_test_mock_secret_key_for_testing_12345"
MOCK_STRIPE_LIVE_PUB = "pk_live_mock_public_key_for_testing_12345"
MOCK_STRIPE_LIVE_SEC = "sk_live_mock_secret_key_for_testing_12345"


class TestValidadoresCredenciales(unittest.TestCase):
    def test_validar_stripe_public_key(self):
        # Válidos
        ok, _ = validar_stripe_public_key(MOCK_STRIPE_PUB)
        self.assertTrue(ok)
        ok_live, _ = validar_stripe_public_key(MOCK_STRIPE_LIVE_PUB)
        self.assertTrue(ok_live)

        # Inválidos: vacío, prefijo erróneo, muy corto, caracteres inválidos
        self.assertFalse(validar_stripe_public_key("")[0])
        self.assertFalse(validar_stripe_public_key("sk_test_123456789012345678901234567890")[0])
        self.assertFalse(validar_stripe_public_key("pk_test_123")[0])
        self.assertFalse(validar_stripe_public_key("pk_test_con espacios y simbolos!@#$%^&*()")[0])

    def test_validar_stripe_secret_key(self):
        # Válidos
        ok, _ = validar_stripe_secret_key(MOCK_STRIPE_SEC)
        self.assertTrue(ok)
        ok_live, _ = validar_stripe_secret_key(MOCK_STRIPE_LIVE_SEC)
        self.assertTrue(ok_live)

        # Inválidos
        self.assertFalse(validar_stripe_secret_key("")[0])
        self.assertFalse(validar_stripe_secret_key(MOCK_STRIPE_PUB)[0])
        self.assertFalse(validar_stripe_secret_key("sk_test_corto")[0])

    def test_validar_esi_facturacion_key(self):
        # Válidos: UUID, prefijo esi_, token alfanumérico
        self.assertTrue(validar_esi_facturacion_key("714d2f92-2d18-4012-a5c7-b7e69ca35a7c")[0])
        self.assertTrue(validar_esi_facturacion_key("esi_test_abcdef1234567890")[0])
        self.assertTrue(validar_esi_facturacion_key("esi_live_secret_token_123456")[0])
        self.assertTrue(validar_esi_facturacion_key("TokenSeguroDePrueba1234567890")[0])

        # Inválidos
        self.assertFalse(validar_esi_facturacion_key("")[0])
        self.assertFalse(validar_esi_facturacion_key("corto")[0])
        self.assertFalse(validar_esi_facturacion_key("token con espacios no permitido")[0])

    def test_validar_esi_facturacion_url(self):
        self.assertTrue(validar_esi_facturacion_url("https://apitest.facturasegura.com.py")[0])
        self.assertTrue(validar_esi_facturacion_url("http://localhost:8000")[0])
        self.assertFalse(validar_esi_facturacion_url("")[0])
        self.assertFalse(validar_esi_facturacion_url("ftp://facturasegura.com")[0])

    def test_validar_esi_ruc(self):
        self.assertTrue(validar_esi_ruc("2595733-3")[0])
        self.assertTrue(validar_esi_ruc("80012345-6")[0])
        self.assertTrue(validar_esi_ruc("2595733")[0])
        self.assertFalse(validar_esi_ruc("")[0])
        self.assertFalse(validar_esi_ruc("abc")[0])


class TestDescompresionYParseo(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_descomprimir_credenciales_zip(self):
        # Crear un zip de prueba con credenciales.txt y text
        zip_path = self.test_dir / "credenciales.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("credenciales.txt", f"STRIPE_PUBLIC_KEY={MOCK_STRIPE_PUB}\n")
            zf.writestr("text", "OTRA_VAR=1\n")

        descomprimido = descomprimir_credenciales_zip(self.test_dir, log_fn=lambda _: None)
        self.assertTrue(descomprimido)
        self.assertTrue((self.test_dir / "credenciales.txt").exists())
        self.assertTrue((self.test_dir / "text").exists())

    def test_buscar_archivo_credenciales_prioridad(self):
        # 1. Cuando existe credenciales.txt
        (self.test_dir / "credenciales.txt").write_text("dummy", encoding="utf-8")
        (self.test_dir / "text").write_text("dummy", encoding="utf-8")
        encontrado = buscar_archivo_credenciales(self.test_dir)
        self.assertEqual(encontrado.name, "credenciales.txt")

        # 2. Cuando no existe credenciales.txt pero sí text
        (self.test_dir / "credenciales.txt").unlink()
        encontrado2 = buscar_archivo_credenciales(self.test_dir)
        self.assertEqual(encontrado2.name, "text")

        # 3. Cuando no existe text pero sí credenciales.text
        (self.test_dir / "text").unlink()
        (self.test_dir / "credenciales.text").write_text("dummy", encoding="utf-8")
        encontrado3 = buscar_archivo_credenciales(self.test_dir)
        self.assertEqual(encontrado3.name, "credenciales.text")

    def test_parsear_secciones_y_alias(self):
        contenido = f"""
[CONFIGURACIÓN PARA VARIABLES DE ENTORNO (backend/.env.stripe)]
STRIPE_PUBLIC_KEY={MOCK_STRIPE_PUB}
STRIPE_SECRET_KEY={MOCK_STRIPE_SEC}
VITE_STRIPE_PUBLISHABLE_KEY={MOCK_STRIPE_PUB}

[CONFIGURACIÓN PARA VARIABLES DE ENTORNO (backend/.env.facturasegura)]
ESI_FACTURACION_API_KEY=esi_test_12345678901234567890
ESI_FACTURACION_URL=https://api.facturacionsegura.com.py/v1
ESI_RUC_EMISOR=80012345-6
FACTURASEGURA_API_KEY=esi_test_12345678901234567890
FACTURASEGURA_SECRET=esi_test_12345678901234567890
"""
        archivo = self.test_dir / "credenciales.txt"
        archivo.write_text(contenido, encoding="utf-8")

        datos = parsear_credenciales(archivo)
        self.assertIn("STRIPE_PUBLIC_KEY", datos["stripe"])
        self.assertIn("STRIPE_PUBLISHABLE_KEY", datos["stripe"])
        self.assertIn("VITE_STRIPE_PUBLISHABLE_KEY", datos["stripe"])
        self.assertIn("STRIPE_SECRET_KEY", datos["stripe"])
        self.assertEqual(datos["facturasegura"]["ESI_FACTURACION_API_KEY"], "esi_test_12345678901234567890")
        self.assertEqual(datos["facturasegura"]["FACTURA_SEGURA_TOKEN"], "esi_test_12345678901234567890")
        self.assertEqual(datos["facturasegura"]["FACTURA_SEGURA_EMISOR_RUC"], "80012345")
        self.assertEqual(datos["facturasegura"]["FACTURA_SEGURA_EMISOR_DV"], "6")

    def test_inyeccion_en_archivos_env(self):
        # Crear estructura de carpetas
        backend_dir = self.test_dir / "backend"
        frontend_dir = self.test_dir / "frontend"
        backend_dir.mkdir(parents=True, exist_ok=True)
        frontend_dir.mkdir(parents=True, exist_ok=True)

        # Crear .example ficticios
        (backend_dir / ".env.example").write_text("DJANGO_SECRET_KEY=demo\n", encoding="utf-8")
        (frontend_dir / ".env.example").write_text("VITE_API_URL=http://localhost:8000\n", encoding="utf-8")
        (self.test_dir / ".env.example").write_text("KEYCLOAK_SERVER_URL=http://localhost:8080\n", encoding="utf-8")

        datos_validados = {
            "stripe": {
                "STRIPE_PUBLIC_KEY": MOCK_STRIPE_PUB,
                "STRIPE_PUBLISHABLE_KEY": MOCK_STRIPE_PUB,
                "STRIPE_SECRET_KEY": MOCK_STRIPE_SEC,
                "VITE_STRIPE_PUBLISHABLE_KEY": MOCK_STRIPE_PUB,
            },
            "facturasegura": {
                "ESI_FACTURACION_API_KEY": "esi_test_12345678901234567890",
                "FACTURA_SEGURA_TOKEN": "esi_test_12345678901234567890",
                "FACTURA_SEGURA_URL": "https://apitest.facturasegura.com.py",
                "ESI_RUC_EMISOR": "80012345-6",
            },
            "todas": {},
            "archivo": "credenciales.txt",
        }

        inyectar_credenciales(
            self.test_dir,
            log_fn=lambda _: None,
            datos_validados=datos_validados,
            interactivo=False
        )

        # Verificar backend/.env
        contenido_backend = (backend_dir / ".env").read_text(encoding="utf-8")
        self.assertIn("STRIPE_SECRET_KEY=sk_test_", contenido_backend)
        self.assertIn("FACTURA_SEGURA_TOKEN=esi_test_", contenido_backend)

        # Verificar frontend/.env
        contenido_frontend = (frontend_dir / ".env").read_text(encoding="utf-8")
        self.assertIn("VITE_STRIPE_PUBLISHABLE_KEY=pk_test_", contenido_frontend)

        # Verificar raíz .env
        contenido_raiz = (self.test_dir / ".env").read_text(encoding="utf-8")
        self.assertIn("STRIPE_PUBLIC_KEY=pk_test_", contenido_raiz)
        self.assertIn("ESI_FACTURACION_API_KEY=esi_test_", contenido_raiz)

        # Verificar backend/.env.stripe y backend/.env.facturasegura
        self.assertTrue((backend_dir / ".env.stripe").exists())
        self.assertTrue((backend_dir / ".env.facturasegura").exists())

    def test_preflight_credenciales_flow(self):
        # Simular que credenciales.zip existe con claves válidas
        zip_path = self.test_dir / "credenciales.zip"
        contenido = f"""
[CONFIGURACIÓN PARA VARIABLES DE ENTORNO (backend/.env.stripe)]
STRIPE_PUBLIC_KEY={MOCK_STRIPE_PUB}
STRIPE_SECRET_KEY={MOCK_STRIPE_SEC}

[CONFIGURACIÓN PARA VARIABLES DE ENTORNO (backend/.env.facturasegura)]
ESI_FACTURACION_API_KEY=714d2f92-2d18-4012-a5c7-b7e69ca35a7c
ESI_FACTURACION_URL=https://api.facturacionsegura.com.py/v1
ESI_RUC_EMISOR=80012345-6
"""
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("credenciales.txt", contenido)

        validadas = preflight_credenciales(self.test_dir)
        self.assertIn("STRIPE_PUBLIC_KEY", validadas["stripe"])
        self.assertEqual(validadas["facturasegura"]["ESI_FACTURACION_API_KEY"], "714d2f92-2d18-4012-a5c7-b7e69ca35a7c")

    def test_alerta_si_no_existe_zip(self):
        logs = []
        descomprimido = descomprimir_credenciales_zip(self.test_dir, log_fn=logs.append)
        self.assertFalse(descomprimido)
        self.assertTrue(any("ALERTA: No se encontró" in msg for msg in logs))

    def test_interactivo_bucle_con_error_y_reintento(self):
        # Simular entradas de usuario: primero valores inválidos, luego valores válidos
        inputs_simulados = [
            "clave_invalida_sin_prefijo",  # Error 1
            "pk_test_corto",               # Error 2
            MOCK_STRIPE_PUB,               # Válido Stripe Pub
            "sk_test_invalido_muy_corto",  # Error 1
            MOCK_STRIPE_SEC,               # Válido Stripe Sec
            "token_invalido_con_espacios ?", # Error 1
            "esi_test_12345678901234567890", # Válido ESI
        ]

        with patch("builtins.input", side_effect=inputs_simulados):
            logs = []
            resultado = obtener_y_validar_credenciales(self.test_dir, log_fn=logs.append, interactivo=True)

        self.assertEqual(resultado["stripe"]["STRIPE_PUBLIC_KEY"], MOCK_STRIPE_PUB)
        self.assertEqual(resultado["stripe"]["STRIPE_SECRET_KEY"], MOCK_STRIPE_SEC)
        self.assertEqual(
            resultado["facturasegura"]["ESI_FACTURACION_API_KEY"],
            "esi_test_12345678901234567890"
        )
        # Verificar que se emitieron logs de error por reintentos
        self.assertTrue(any("[ERROR]" in msg for msg in logs))


if __name__ == "__main__":
    unittest.main()
