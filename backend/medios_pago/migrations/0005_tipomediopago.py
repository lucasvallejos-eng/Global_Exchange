from django.db import migrations, models


def crear_tipos_globales(apps, schema_editor):
    TipoMedioPago = apps.get_model("medios_pago", "TipoMedioPago")
    for clave, nombre in (
        ("TARJETA_CREDITO", "Tarjeta de Crédito"),
        ("TRANSFERENCIA", "Transferencia Bancaria"),
        ("BILLETERA_DIGITAL", "Billetera Digital"),
    ):
        TipoMedioPago.objects.get_or_create(
            clave=clave, defaults={"nombre": nombre, "activo": True}
        )


class Migration(migrations.Migration):
    dependencies = [("medios_pago", "0004_alter_mediopago_tipo")]

    operations = [
        migrations.CreateModel(
            name="TipoMedioPago",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("clave", models.CharField(max_length=30, unique=True)),
                ("nombre", models.CharField(max_length=80)),
                ("activo", models.BooleanField(default=True)),
            ],
            options={"ordering": ["id"]},
        ),
        migrations.RunPython(crear_tipos_globales, migrations.RunPython.noop),
    ]
