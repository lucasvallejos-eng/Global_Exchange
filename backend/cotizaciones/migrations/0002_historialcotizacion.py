from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("cotizaciones", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="HistorialCotizacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("precio_compra_anterior", models.DecimalField(decimal_places=2, max_digits=12)),
                ("precio_compra_nuevo", models.DecimalField(decimal_places=2, max_digits=12)),
                ("precio_venta_anterior", models.DecimalField(decimal_places=2, max_digits=12)),
                ("precio_venta_nuevo", models.DecimalField(decimal_places=2, max_digits=12)),
                ("fecha_registro", models.DateTimeField(auto_now_add=True)),
                ("administrador", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("moneda", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="historial_cotizaciones", to="monedas.moneda")),
            ],
        ),
    ]
