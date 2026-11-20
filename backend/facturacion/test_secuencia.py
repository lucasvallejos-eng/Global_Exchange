"""Tests del servicio de control y numeración secuencial de facturas electrónicas.

Valida:
1. Secuencia correlativa (EEE-PPP-NNNNNNN).
2. Estado de negocio: última factura 387 -> siguiente 388.
3. Cantidad disponible permanente (con última 387 y límite 393, restan 6).
4. Validación y bloqueo estricto al alcanzar o superar el límite 393 (TalonarioAgotadoError).
5. Estructura del payload con dEst, dPunExp y dNumDoc para Factura Segura.
6. Persistencia y atomicidad en base de datos.
"""
from django.test import TestCase

from facturacion.models import SecuenciaFactura
from facturacion.secuencia import (
    GestorSecuenciaFactura,
    TalonarioAgotadoError,
    cantidad_disponible,
    generar_payload_siguiente_factura,
    inyectar_payload_generar_de,
    validar_limite_disponible,
)


class SecuenciaFacturaTest(TestCase):
    """Pruebas del servicio de secuencia y reglas de negocio del talonario."""

    def setUp(self):
        super().setUp()
        # Aseguramos el estado inicial exacto de negocio:
        # Última factura usada: 387, rango autorizado: 382 a 393
        self.talonario, _ = SecuenciaFactura.objects.update_or_create(
            establecimiento="001",
            punto_expedicion="003",
            defaults={
                "ultimo_numero": 387,
                "numero_inicio": 382,
                "numero_fin": 393,
                "activo": True,
            },
        )
        self.gestor = GestorSecuenciaFactura(
            establecimiento="001", punto_expedicion="003"
        )

    def test_estado_inicial_y_cantidad_disponible(self):
        """Con última factura 387 y límite 393, deben quedar exactamente 6 facturas disponibles."""
        self.assertEqual(self.talonario.ultimo_numero, 387)
        self.assertEqual(self.talonario.numero_fin, 393)
        self.assertEqual(self.gestor.consultar_cantidad_disponible(), 6)
        self.assertEqual(cantidad_disponible("001", "003"), 6)
        self.assertFalse(self.talonario.esta_agotado)

    def test_siguiente_factura_obligatoria_es_388(self):
        """La siguiente factura a generar debe ser la 001-003-0000388."""
        payload = generar_payload_siguiente_factura(
            establecimiento="001", punto_expedicion="003", reservar=False
        )
        self.assertEqual(payload["dEst"], "001")
        self.assertEqual(payload["dPunExp"], "003")
        self.assertEqual(payload["dNumDoc"], "0000388")
        self.assertEqual(payload["numero"], 388)
        self.assertEqual(payload["numero_completo"], "001-003-0000388")
        self.assertEqual(payload["cantidad_disponible"], 6)

        # Como reservar=False, no debió modificar la base de datos
        self.talonario.refresh_from_db()
        self.assertEqual(self.talonario.ultimo_numero, 387)

    def test_reserva_incrementa_secuencia_y_reduce_disponibles(self):
        """Al reservar la 388, el último número pasa a 388 y restan 5 disponibles."""
        payload = generar_payload_siguiente_factura(
            establecimiento="001", punto_expedicion="003", reservar=True
        )
        self.assertEqual(payload["dNumDoc"], "0000388")
        self.assertEqual(payload["numero"], 388)
        self.assertEqual(payload["cantidad_disponible"], 5)

        self.talonario.refresh_from_db()
        self.assertEqual(self.talonario.ultimo_numero, 388)
        self.assertEqual(cantidad_disponible("001", "003"), 5)

    def test_consumo_secuencial_hasta_agotar_talonario(self):
        """Consume desde 388 hasta 393 inclusive, validando la correlatividad y la cantidad restante."""
        secuencia_esperada = [
            (388, "0000388", 5),
            (389, "0000389", 4),
            (390, "0000390", 3),
            (391, "0000391", 2),
            (392, "0000392", 1),
            (393, "0000393", 0),  # Última factura autorizada
        ]

        for numero, doc_esperado, restantes_esperados in secuencia_esperada:
            datos = self.gestor.obtener_siguiente_factura(reservar=True)
            self.assertEqual(datos.numero, numero)
            self.assertEqual(datos.dNumDoc, doc_esperado)
            self.assertEqual(datos.cantidad_disponible, restantes_esperados)
            self.assertEqual(
                datos.numero_completo, f"001-003-{doc_esperado}"
            )

        self.talonario.refresh_from_db()
        self.assertEqual(self.talonario.ultimo_numero, 393)
        self.assertEqual(self.talonario.cantidad_disponible, 0)
        self.assertTrue(self.talonario.esta_agotado)

    def test_superar_limite_lanza_excepcion_talonario_agotado(self):
        """Al intentar generar una factura luego de alcanzar la 393, debe lanzar TalonarioAgotadoError."""
        # Colocamos el talonario en la última factura autorizada (393)
        self.talonario.ultimo_numero = 393
        self.talonario.save()

        # Validar límite debe fallar
        with self.assertRaises(TalonarioAgotadoError) as ctx:
            validar_limite_disponible("001", "003")
        self.assertIn("Talonario agotado", str(ctx.exception))
        self.assertIn("001-003-0000393", str(ctx.exception))
        self.assertIn("0 facturas", str(ctx.exception))

        # Intentar obtener la siguiente factura debe lanzar la misma excepción
        with self.assertRaises(TalonarioAgotadoError):
            generar_payload_siguiente_factura(
                establecimiento="001", punto_expedicion="003", reservar=True
            )

        # La base de datos no debe incrementarse más allá del límite
        self.talonario.refresh_from_db()
        self.assertEqual(self.talonario.ultimo_numero, 393)

    def test_inyectar_payload_generar_de(self):
        """Inyecta dEst, dPunExp y dNumDoc listos en el JSON de generar_de de Factura Segura."""
        payload_base_de = {
            "iTipEmi": "1",
            "iTiDE": "1",
            "dNumTim": "02595733",
            "gCamItem": [],
        }

        payload_actualizado = inyectar_payload_generar_de(
            payload_base_de,
            establecimiento="001",
            punto_expedicion="003",
            reservar=True,
        )

        self.assertEqual(payload_actualizado["dEst"], "001")
        self.assertEqual(payload_actualizado["dPunExp"], "003")
        self.assertEqual(payload_actualizado["dNumDoc"], "0000388")
        self.assertIn("dNumTim", payload_actualizado)

        self.talonario.refresh_from_db()
        self.assertEqual(self.talonario.ultimo_numero, 388)

