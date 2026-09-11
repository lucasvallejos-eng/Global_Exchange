from decimal import Decimal

from django.db import migrations


def seed_default_segments(apps, schema_editor):
    SegmentoCliente = apps.get_model("comisiones", "SegmentoCliente")
    defaults = {
        "Minorista": Decimal("0.05"),
        "Mayorista": Decimal("0.10"),
        "VIP": Decimal("0.15"),
    }
    for nombre, descuento in defaults.items():
        segmento, _ = SegmentoCliente.objects.get_or_create(
            nombre=nombre,
            defaults={
                "porcentaje_comision": Decimal("0"),
                "descuento_compra": descuento,
                "descripcion": f"Descuento de compra para clientes {nombre.lower()}.",
                "activo": True,
            },
        )
        if segmento.descuento_compra != descuento:
            segmento.descuento_compra = descuento
            segmento.save(update_fields=["descuento_compra"])


class Migration(migrations.Migration):
    dependencies = [
        ("comisiones", "0002_segmentocliente_descuento_compra"),
    ]

    operations = [
        migrations.RunPython(seed_default_segments, migrations.RunPython.noop),
    ]
