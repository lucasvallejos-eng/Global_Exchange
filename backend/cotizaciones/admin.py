"""Registro de Cotizacion en el panel de administración de Django."""
from datetime import timedelta

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Cotizacion, HistorialCotizacion


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    """Configuración del panel de administración para la gestión de cotizaciones.

    Permite consultar, filtrar y modificar las tasas de cambio activas e históricas.
    Integra la validación del bloqueo temporal de 1 hora al modificar precios y genera
    automáticamente un registro en el historial de auditoría al guardar los cambios.

    Attributes:
        list_display (tuple): Campos mostrados en la vista de lista del admin.
        list_filter (tuple): Filtros laterales aplicables por estado activo y moneda.
        search_fields (tuple): Campos habilitados para búsqueda por código o nombre de moneda.
        date_hierarchy (str): Navegación jerárquica por fechas basadas en la creación.
    """
    list_display = ("moneda", "precio_compra", "precio_venta", "activa", "fecha")
    list_filter = ("activa", "moneda")
    search_fields = ("moneda__codigo", "moneda__nombre")
    date_hierarchy = "fecha"

    def save_model(self, request, obj, form, change):
        """Sobrescribe la lógica de guardado en el admin para aplicar reglas y auditoría.

        Valida que haya transcurrido al menos 1 hora desde la última modificación sobre la
        moneda si los precios de compra o venta sufrieron cambios. Al persistir con éxito,
        registra la modificación en el modelo ``HistorialCotizacion`` asignando al usuario
        administrador en sesión.

        Args:
            request (HttpRequest): Solicitud HTTP con la sesión del usuario administrador.
            obj (Cotizacion): Instancia del modelo a crear o guardar.
            form (ModelForm): Formulario de edición procesado por Django admin.
            change (bool): True si el objeto ya existía (edición), False si es un alta nueva.

        Raises:
            ValidationError: Si se intenta modificar el precio de compra o venta antes de que
                transcurra el lapso de 1 hora desde el último cambio registrado.
        """
        anterior = None
        if change:
            anterior = Cotizacion.objects.get(pk=obj.pk)
            restante = timedelta(hours=1) - (
                timezone.now() - obj.moneda.fecha_actualizacion
            )
            if (
                (obj.precio_compra != anterior.precio_compra
                 or obj.precio_venta != anterior.precio_venta)
                and restante.total_seconds() > 0
            ):
                minutos = max(1, int((restante.total_seconds() + 59) // 60))
                raise ValidationError(
                    "No se puede actualizar la cotización. Debe transcurrir "
                    f"al menos 1 hora desde el último cambio. Tiempo restante: "
                    f"{minutos} minutos."
                )

        super().save_model(request, obj, form, change)
        if anterior and (
            obj.precio_compra != anterior.precio_compra
            or obj.precio_venta != anterior.precio_venta
        ):
            HistorialCotizacion.objects.create(
                moneda=obj.moneda,
                administrador=request.user,
                precio_compra_anterior=anterior.precio_compra,
                precio_compra_nuevo=obj.precio_compra,
                precio_venta_anterior=anterior.precio_venta,
                precio_venta_nuevo=obj.precio_venta,
            )
            obj.moneda.save(update_fields=["fecha_actualizacion"])


@admin.register(HistorialCotizacion)
class HistorialCotizacionAdmin(admin.ModelAdmin):
    """Configuración del panel de administración para el historial de auditoría.

    Expone el registro histórico inmutable de los cambios de tasas. Marca todos los
    campos como de solo lectura (``readonly_fields``) para impedir alteraciones manuales.

    Attributes:
        list_display (tuple): Atributos visibles en el listado principal del historial.
        list_filter (tuple): Filtros laterales por moneda y administrador responsable.
        date_hierarchy (str): Jerarquía temporal de exploración basada en `fecha_registro`.
        readonly_fields (list): Lista dinámica que deshabilita la edición de todos los campos.
    """
    list_display = (
        "moneda",
        "administrador",
        "precio_compra_anterior",
        "precio_compra_nuevo",
        "precio_venta_anterior",
        "precio_venta_nuevo",
        "fecha_registro",
    )
    list_filter = ("moneda", "administrador")
    date_hierarchy = "fecha_registro"
    readonly_fields = [field.name for field in HistorialCotizacion._meta.fields]
