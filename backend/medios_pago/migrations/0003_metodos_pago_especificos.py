from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("medios_pago", "0002_alter_mediopago_alias_and_more")]

    operations = [
        migrations.AddField(
            model_name="mediopago",
            name="fecha_actualizacion",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.CreateModel(
            name="TarjetaCredito",
            fields=[
                ("mediopago_ptr", models.OneToOneField(auto_created=True, on_delete=models.CASCADE, parent_link=True, primary_key=True, serialize=False, to="medios_pago.mediopago")),
                ("nombre_titular", models.CharField(max_length=120)),
                ("alias_tarjeta", models.CharField(max_length=80)),
                ("numero_tarjeta", models.CharField(help_text="Token o número protegido", max_length=255)),
                ("fecha_vencimiento", models.CharField(help_text="Formato MM/YY", max_length=5)),
                ("codigo_seguridad", models.CharField(help_text="Valor protegido", max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name="TransferenciaBancaria",
            fields=[
                ("mediopago_ptr", models.OneToOneField(auto_created=True, on_delete=models.CASCADE, parent_link=True, primary_key=True, serialize=False, to="medios_pago.mediopago")),
                ("numero_cuenta_origen", models.CharField(max_length=100)),
                ("banco_origen", models.CharField(max_length=120)),
                ("titular_origen", models.CharField(max_length=120)),
                ("numero_cuenta_destino", models.CharField(max_length=100)),
                ("banco_destino", models.CharField(max_length=120)),
                ("titular_destino", models.CharField(max_length=120)),
            ],
        ),
        migrations.CreateModel(
            name="BilleteraDigital",
            fields=[
                ("mediopago_ptr", models.OneToOneField(auto_created=True, on_delete=models.CASCADE, parent_link=True, primary_key=True, serialize=False, to="medios_pago.mediopago")),
                ("plataforma", models.CharField(max_length=80)),
                ("identificador_cuenta", models.CharField(max_length=255)),
                ("titular", models.CharField(max_length=120)),
            ],
        ),
    ]
