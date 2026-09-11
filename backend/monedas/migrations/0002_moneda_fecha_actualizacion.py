from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("monedas", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="moneda",
            name="fecha_actualizacion",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
