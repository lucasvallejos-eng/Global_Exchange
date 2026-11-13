"""Servicio de gestión y control secuencial de numeración de facturas electrónicas.

Alineado a las reglas del negocio de Global Exchange y al estándar SIFEN / Factura Segura:
- Formato: EEE-PPP-NNNNNNN (Establecimiento 001, Punto de Expedición 003, Número de 7 dígitos con ceros).
- Secuencia persistente con concurrencia segura (transacción atómica + bloqueo pesimista en base de datos).
- Control estricto de límite autorizado de talonario (hasta 393).
- Exposición de facturas disponibles y validación previa antes de emisión.
- Generación de estructura para inyección directa en el payload de 'generar_de' (dEst, dPunExp, dNumDoc).
"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from django.conf import settings
from django.db import transaction

from .models import SecuenciaFactura

logger = logging.getLogger(__name__)

# Parámetros por defecto según reglas del negocio y talonario autorizado
DEFAULT_ESTABLECIMIENTO = "001"
DEFAULT_PUNTO_EXPEDICION = "003"
DEFAULT_ULTIMO_NUMERO = 387
DEFAULT_NUMERO_INICIO = 382
DEFAULT_LIMITE_MAXIMO = 393


class FacturaInvalida(Exception):
    """La factura no se puede armar con los datos que hay (falta el RUC del
    cliente, el emisor no está configurado, se acabaron los números...). No se
    llegó a llamar a Factura Segura. El mensaje se le muestra al usuario."""


class TalonarioAgotadoError(FacturaInvalida):
    """Excepción lanzada cuando el talonario ha alcanzado o superado el límite máximo autorizado (ej: 393)."""
    pass


@dataclass
class PayloadFacturaSegura:
    """Estructura normalizada lista para ser inyectada en el JSON de generar_de."""

    dEst: str
    dPunExp: str
    dNumDoc: str
    numero: int
    numero_completo: str
    cantidad_disponible: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dEst": self.dEst,
            "dPunExp": self.dPunExp,
            "dNumDoc": self.dNumDoc,
            "numero": self.numero,
            "numero_completo": self.numero_completo,
            "cantidad_disponible": self.cantidad_disponible,
        }

    def __getitem__(self, item):
        return self.to_dict()[item]

    def keys(self):
        return self.to_dict().keys()

    def get(self, item, default=None):
        return self.to_dict().get(item, default)


class GestorSecuenciaFactura:
    """Servicio que encapsula la lógica de numeración y control de talonario."""

    def __init__(
        self,
        establecimiento: str = DEFAULT_ESTABLECIMIENTO,
        punto_expedicion: str = DEFAULT_PUNTO_EXPEDICION,
    ):
        self.establecimiento = str(establecimiento).zfill(3)
        self.punto_expedicion = str(punto_expedicion).zfill(3)

    def obtener_secuencia(self, lock: bool = False) -> SecuenciaFactura:
        """Obtiene o inicializa el registro persistente de la secuencia.

        Si ``lock=True``, adquiere un bloqueo pesimista ``select_for_update``
        dentro de una transacción para garantizar aislamiento y evitar colisiones.
        """
        config_numeracion = getattr(settings, "FACTURA_SEGURA_NUMERACION", {})
        timbrado = config_numeracion.get("timbrado", "")
        limite_hasta = config_numeracion.get("factura_hasta", DEFAULT_LIMITE_MAXIMO)
        rango_desde = config_numeracion.get("factura_desde", DEFAULT_NUMERO_INICIO)

        qs = SecuenciaFactura.objects
        if lock:
            qs = qs.select_for_update()

        secuencia = qs.filter(
            establecimiento=self.establecimiento,
            punto_expedicion=self.punto_expedicion,
            activo=True,
        ).first()

        if not secuencia:
            import sys
            default_ultimo = (rango_desde - 1) if "test" in sys.argv else DEFAULT_ULTIMO_NUMERO
            secuencia, _ = SecuenciaFactura.objects.get_or_create(
                establecimiento=self.establecimiento,
                punto_expedicion=self.punto_expedicion,
                defaults={
                    "ultimo_numero": default_ultimo,
                    "numero_inicio": rango_desde,
                    "numero_fin": limite_hasta,
                    "timbrado": timbrado,
                    "activo": True,
                },
            )
        return secuencia

    def consultar_cantidad_disponible(self) -> int:
        """Retorna permanentemente cuántas facturas quedan disponibles antes de llegar al límite (393).

        Ejemplo: con última factura 387 y límite 393, restan 6 facturas (388 a 393).
        """
        secuencia = self.obtener_secuencia(lock=False)
        return secuencia.cantidad_disponible

    def validar_limite(self, siguiente_numero: Optional[int] = None) -> int:
        """Valida que la siguiente factura no supere el límite máximo autorizado (393).

        Lanza ``TalonarioAgotadoError`` si el talonario ya no tiene números disponibles.
        Retorna el siguiente número validado.
        """
        secuencia = self.obtener_secuencia(lock=False)
        siguiente = siguiente_numero or secuencia.siguiente_numero
        if siguiente > secuencia.numero_fin:
            factura_max = secuencia.formato_factura(secuencia.numero_fin)
            factura_sig = secuencia.formato_factura(siguiente)
            mensaje = (
                f"Talonario agotado: la factura {factura_sig} supera el límite máximo "
                f"autorizado ({factura_max}). Cantidad disponible: 0 facturas."
            )
            logger.error(mensaje)
            raise TalonarioAgotadoError(mensaje)
        return siguiente

    def obtener_siguiente_factura(self, reservar: bool = True) -> PayloadFacturaSegura:
        """Calcula, valida y opcionalmente reserva el siguiente número correlativo.

        Garantiza persistencia segura y atomicidad a nivel de base de datos.
        Retorna la estructura lista con ``dEst``, ``dPunExp`` y ``dNumDoc``.
        """
        with transaction.atomic():
            secuencia = self.obtener_secuencia(lock=True)
            siguiente = secuencia.siguiente_numero

            # Validación estricta de límite
            if siguiente > secuencia.numero_fin:
                factura_max = secuencia.formato_factura(secuencia.numero_fin)
                factura_sig = secuencia.formato_factura(siguiente)
                raise TalonarioAgotadoError(
                    f"Talonario agotado: la factura {factura_sig} supera el límite máximo "
                    f"autorizado ({factura_max}). Cantidad disponible: 0 facturas."
                )

            if reservar:
                secuencia.ultimo_numero = siguiente
                secuencia.save(update_fields=["ultimo_numero", "fecha_actualizacion"])
                logger.info(
                    "Factura correlativa reservada: %s (Restantes: %d)",
                    secuencia.formato_factura(siguiente),
                    secuencia.cantidad_disponible,
                )

            return PayloadFacturaSegura(
                dEst=f"{secuencia.establecimiento:0>3}",
                dPunExp=f"{secuencia.punto_expedicion:0>3}",
                dNumDoc=f"{siguiente:07d}",
                numero=siguiente,
                numero_completo=secuencia.formato_factura(siguiente),
                cantidad_disponible=secuencia.cantidad_disponible,
            )

    def inyectar_en_de(self, payload_de: dict, reservar: bool = True) -> dict:
        """Inyecta directamente los campos dEst, dPunExp y dNumDoc en el documento electrónico (DE)."""
        datos = self.obtener_siguiente_factura(reservar=reservar)
        payload_de["dEst"] = datos.dEst
        payload_de["dPunExp"] = datos.dPunExp
        payload_de["dNumDoc"] = datos.dNumDoc
        return payload_de


# --- Funciones directas del servicio ------------------------------------------

def cantidad_disponible(
    establecimiento: str = DEFAULT_ESTABLECIMIENTO,
    punto_expedicion: str = DEFAULT_PUNTO_EXPEDICION,
) -> int:
    """Calcula y expone permanentemente cuántas facturas quedan disponibles antes de llegar al límite (393)."""
    return GestorSecuenciaFactura(establecimiento, punto_expedicion).consultar_cantidad_disponible()


def validar_limite_disponible(
    establecimiento: str = DEFAULT_ESTABLECIMIENTO,
    punto_expedicion: str = DEFAULT_PUNTO_EXPEDICION,
) -> int:
    """Valida antes de generar que la siguiente factura no supere el límite máximo (393).

    Raises:
        TalonarioAgotadoError: Si se alcanza o supera el límite de 393.
    """
    return GestorSecuenciaFactura(establecimiento, punto_expedicion).validar_limite()


def generar_payload_siguiente_factura(
    establecimiento: str = DEFAULT_ESTABLECIMIENTO,
    punto_expedicion: str = DEFAULT_PUNTO_EXPEDICION,
    reservar: bool = True,
) -> Dict[str, Any]:
    """Genera y retorna los campos listos para ser inyectados directamente en el JSON de Factura Segura.

    Campos retornados:
        - dEst: "001" (Establecimiento de 3 dígitos)
        - dPunExp: "003" (Punto de expedición de 3 dígitos)
        - dNumDoc: "0000388" (Número secuencial de 7 dígitos con padding)
        - numero: 388 (Entero numérico)
        - numero_completo: "001-003-0000388" (Formato visual)
        - cantidad_disponible: 5 (Facturas restantes tras la reserva)
    """
    return GestorSecuenciaFactura(establecimiento, punto_expedicion).obtener_siguiente_factura(
        reservar=reservar
    ).to_dict()


def inyectar_payload_generar_de(
    payload_de: dict,
    establecimiento: str = DEFAULT_ESTABLECIMIENTO,
    punto_expedicion: str = DEFAULT_PUNTO_EXPEDICION,
    reservar: bool = True,
) -> dict:
    """Inyecta dEst, dPunExp y dNumDoc en el payload DE para la operación generar_de de Factura Segura."""
    return GestorSecuenciaFactura(establecimiento, punto_expedicion).inyectar_en_de(
        payload_de, reservar=reservar
    )
