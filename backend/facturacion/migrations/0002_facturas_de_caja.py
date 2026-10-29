import django.db.models.deletion
from django.db import migrations, models


def copiar_cliente(apps, schema_editor):
    """Las facturas que ya existían son todas de la web: su cliente es el de
    la transacción."""
    Factura = apps.get_model("facturacion", "Factura")
    for factura in Factura.objects.select_related("transaccion"):
        factura.cliente_id = factura.transaccion.cliente_id
        factura.save(update_fields=["cliente"])


class Migration(migrations.Migration):
    """La factura puede ser de una operación de la caja, y guarda su cliente."""

    dependencies = [
        ('caja', '0007_usuario_apertura'),
        ('clientes', '0003_cliente_ruc'),
        ('facturacion', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='factura',
            name='transaccion',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='factura', to='operaciones.transaccion'),
        ),
        migrations.AddField(
            model_name='factura',
            name='compra_caja',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='factura', to='caja.compracaja'),
        ),
        migrations.AddField(
            model_name='factura',
            name='venta_caja',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='factura', to='caja.ventacaja'),
        ),
        # El cliente entra vacío, se completa y recién después se vuelve obligatorio.
        migrations.AddField(
            model_name='factura',
            name='cliente',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name='facturas', to='clientes.cliente'),
        ),
        migrations.RunPython(copiar_cliente, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='factura',
            name='cliente',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='facturas', to='clientes.cliente'),
        ),
    ]
