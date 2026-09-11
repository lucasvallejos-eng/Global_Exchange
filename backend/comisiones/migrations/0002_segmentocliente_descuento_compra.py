from decimal import Decimal

from django.db import migrations, models
import django.core.validators


def cargar_descuentos_iniciales(apps, schema_editor):
    SegmentoCliente = apps.get_model("comisiones", "SegmentoCliente")
    descuentos = {
        "Minorista": Decimal("0.05"),
        "Mayorista": Decimal("0.10"),
        "VIP": Decimal("0.15"),
    }
    for nombre, descuento in descuentos.items():
        SegmentoCliente.objects.filter(nombre__iexact=nombre).update(
            descuento_compra=descuento
        )


class Migration(migrations.Migration):
    dependencies = [
        ("comisiones", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="segmentocliente",
            name="descuento_compra",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Descuento aplicado a operaciones de compra, entre 0 y 1.",
                max_digits=4,
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(1),
                ],
            ),
        ),
        migrations.RunPython(cargar_descuentos_iniciales, migrations.RunPython.noop),
    ]
