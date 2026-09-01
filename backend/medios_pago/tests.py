from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from .models import MedioPago
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings

User = get_user_model()


class MedioPagoModelTest(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(
            username="cliente1",
            email="cliente1@example.com"
        )

    def test_creacion_medio_pago_exitoso(self):
        """Verifica que el medio de pago se cree correctamente asignado al usuario."""
        medio = MedioPago.objects.create(
            usuario=self.usuario,
            tipo="TARJETA_CREDITO",
            alias="Mi Tarjeta Itaú",
            numero_cuenta_o_tarjeta="****1234",
            banco_o_proveedor="Itaú"
        )
        self.assertEqual(medio.usuario, self.usuario)
        self.assertEqual(medio.alias, "Mi Tarjeta Itaú")
        self.assertTrue(medio.activo)

    def test_borrado_logico_medio_pago(self):
        """Verifica que el borrado cambie activa a False sin eliminarlo de la BD."""
        medio = MedioPago.objects.create(
            usuario=self.usuario,
            tipo="CUENTA_BANCARIA",
            alias="Cuenta Cajas",
            numero_cuenta_o_tarjeta="123456789"
        )
        medio.activo = False
        medio.save()

        self.assertEqual(MedioPago.objects.count(), 1)
        self.assertFalse(MedioPago.objects.get(id=medio.id).activo)


class MedioPagoViewsTest(TestCase):
    def setUp(self):
        self.cliente_a = User.objects.create_user(username="cliente_a")
        self.cliente_b = User.objects.create_user(username="cliente_b")

        self.medio_a = MedioPago.objects.create(
            usuario=self.cliente_a,
            tipo="TARJETA_DEBITO",
            alias="Tarjeta Cliente A",
            numero_cuenta_o_tarjeta="1111"
        )

    def test_acceso_protegido_sin_autenticacion(self):
        """Verifica que usuarios no autenticados no puedan listar ni editar."""
        response = self.client.get(reverse('listar_medios_pago'))
        self.assertNotEqual(response.status_code, 200)

    def test_aislamiento_entre_clientes(self):
        """Garantiza que un cliente no pueda editar un medio de pago que pertenece a otro."""
        self.client.force_login(self.cliente_b)
        
        # El cliente B intenta editar la tarjeta del cliente A
        response = self.client.post(
            reverse('editar_medio_pago', kwargs={'pk': self.medio_a.pk}),
            {'alias': 'Intento Hackeo'}
        )
        self.assertEqual(response.status_code, 403)
        
        # Confirmar que el alias no cambió en la base de datos
        self.medio_a.refresh_from_db()
        self.assertEqual(self.medio_a.alias, "Tarjeta Cliente A")

@override_settings(MIDDLEWARE=[
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
])

class MedioPagoAvanceViewsTest(TestCase):
    def setUp(self):
        self.cliente_1 = User.objects.create_user(username="cliente_1")
        self.cliente_2 = User.objects.create_user(username="cliente_2")

        grupo_cliente, _ = Group.objects.get_or_create(name="cliente")
        self.cliente_1.groups.add(grupo_cliente)
        self.cliente_2.groups.add(grupo_cliente)

        # Medio de pago activo de cliente 1
        self.medio_activo = MedioPago.objects.create(
            usuario=self.cliente_1,
            tipo="TARJETA_CREDITO",
            alias="Tarjeta Cliente 1",
            numero_cuenta_o_tarjeta="1111",
            activo=True
        )

        # Medio de pago inactivo de cliente 1
        self.medio_inactivo = MedioPago.objects.create(
            usuario=self.cliente_1,
            tipo="CUENTA_BANCARIA",
            alias="Tarjeta Inactiva",
            numero_cuenta_o_tarjeta="2222",
            activo=False
        )

        # Medio de pago de cliente 2
        self.medio_cliente_2 = MedioPago.objects.create(
            usuario=self.cliente_2,
            tipo="TARJETA_DEBITO",
            alias="Tarjeta Cliente 2",
            numero_cuenta_o_tarjeta="3333",
            activo=True
        )




    def test_crear_medio_pago_asigna_usuario_actual(self):
        """Verifica que la vista asigne automáticamente el usuario autenticado al crear."""
        self.client.force_login(self.cliente_1)
        data = {
            'tipo': 'BILLETERA_DIGITAL',
            'alias': 'Mi Tigo Money',
            'numero': '0981123456',
            'banco': 'Tigo'
        }
        response = self.client.post(reverse('crear_medio_pago'), data)
        self.assertEqual(response.status_code, 302) 

        nuevo_medio = MedioPago.objects.get(alias='Mi Tigo Money')
        self.assertEqual(nuevo_medio.usuario, self.cliente_1)

    def test_lista_solo_muestra_medios_activos_del_usuario(self):
        """Verifica que el cliente no vea registros inactivos ni de otros clientes."""
        self.client.force_login(self.cliente_1)
        response = self.client.get(reverse('listar_medios_pago'))

        print("Redirigido a:", response.get('Location'))

        self.assertEqual(response.status_code, 200)
        medios_en_contexto = response.context['medios']

        self.assertIn(self.medio_activo, medios_en_contexto)
        self.assertNotIn(self.medio_inactivo, medios_en_contexto)
        self.assertNotIn(self.medio_cliente_2, medios_en_contexto)

    def test_vista_eliminar_aplica_soft_delete(self):
        """Verifica que llamar a la vista de eliminación deshabilite el medio de pago."""
        self.client.force_login(self.cliente_1)
        response = self.client.post(reverse('eliminar_medio_pago', kwargs={'pk': self.medio_activo.pk}))
        
        self.assertEqual(response.status_code, 302)
        self.medio_activo.refresh_from_db()
        self.assertFalse(self.medio_activo.activo)