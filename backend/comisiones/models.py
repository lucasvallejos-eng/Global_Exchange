from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class SegmentoCliente(models.Model):
    """Segmento comercial de clientes y el porcentaje de comisión que le toca.

    Cubre el ítem "Configuración de porcentajes de comisión por tipo de
    cliente" del alcance del Sprint 2. Acá vive solo la **configuración**: el
    cálculo de la comisión sobre una operación de compra/venta corresponde al
    Sprint 3, según la guía de la cátedra.

    El segmento se guarda aparte y todavía no se asocia al modelo ``Cliente``.
    Esa relación se agrega cuando haga falta aplicar la comisión, para no
    tocar el modelo de clientes antes de tiempo.
    """

    nombre = models.CharField(
        max_length=50,
        unique=True,
        help_text="Nombre del segmento. Por ejemplo: VIP, Corporativo, Minorista.",
    )
    porcentaje_comision = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Porcentaje que se le cobra a este segmento, entre 0 y 100.",
    )
    descripcion = models.CharField(max_length=200, blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['porcentaje_comision', 'nombre']
        verbose_name = "segmento de cliente"
        verbose_name_plural = "segmentos de cliente"

    def __str__(self):
        return f"{self.nombre} ({self.porcentaje_comision}%)"

    def clean(self):
        """Valida el nombre más allá de lo que ya cubre el campo.

        ``unique=True`` no distingue mayúsculas de minúsculas en SQLite, así
        que "VIP" y "vip" pasarían como dos segmentos distintos. Se comprueba
        acá para que no queden duplicados que confundan al configurar.
        """
        if self.nombre:
            self.nombre = self.nombre.strip()
            repetidos = SegmentoCliente.objects.filter(nombre__iexact=self.nombre)
            if self.pk:
                repetidos = repetidos.exclude(pk=self.pk)
            if repetidos.exists():
                raise ValidationError(
                    {'nombre': f'Ya existe un segmento llamado "{self.nombre}".'}
                )
