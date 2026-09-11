import json
import time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse

from clientes.models import Cliente
from .models import SegmentoCliente

User = get_user_model()


class SegmentoClienteModeloTest(TestCase):
    """Validaciones del modelo de segmentos."""

    def test_porcentaje_dentro_del_rango_es_valido(self):
        # La migración 0003 siembra Minorista/Mayorista/VIP de fábrica; se
        # vacía la tabla para que este test siga probando sobre una tabla
        # limpia, como cuando se escribió (no afecta a los demás tests: cada
        # uno corre en su propia transacción, que se descarta al terminar).
        SegmentoCliente.objects.all().delete()
        segmento = SegmentoCliente(nombre="VIP", porcentaje_comision=1.50)
        segmento.full_clean()
        segmento.save()
        self.assertEqual(SegmentoCliente.objects.count(), 1)

    def test_rechaza_porcentaje_negativo(self):
        segmento = SegmentoCliente(nombre="Raro", porcentaje_comision=-5)
        with self.assertRaises(ValidationError):
            segmento.full_clean()

    def test_rechaza_porcentaje_mayor_a_cien(self):
        segmento = SegmentoCliente(nombre="Imposible", porcentaje_comision=150)
        with self.assertRaises(ValidationError):
            segmento.full_clean()

    def test_rechaza_nombre_repetido_ignorando_mayusculas(self):
        """unique=True no distingue mayúsculas en SQLite, lo cubre clean()."""
        SegmentoCliente.objects.all().delete()
        SegmentoCliente.objects.create(nombre="VIP", porcentaje_comision=1)
        repetido = SegmentoCliente(nombre="vip", porcentaje_comision=2)
        with self.assertRaises(ValidationError):
            repetido.full_clean()

    def test_editar_un_segmento_no_choca_consigo_mismo(self):
        """Al editar, el propio registro no debe contar como duplicado."""
        SegmentoCliente.objects.all().delete()
        segmento = SegmentoCliente.objects.create(nombre="VIP", porcentaje_comision=1)
        segmento.porcentaje_comision = 2
        segmento.full_clean()  # no debe lanzar
        segmento.save()
        self.assertEqual(SegmentoCliente.objects.get(pk=segmento.pk).porcentaje_comision, 2)


class SegmentoClienteVistasTest(TestCase):
    """El ABM de segmentos, desde las pantallas."""

    def setUp(self):
        grupo_admin, _ = Group.objects.get_or_create(name="administrador")
        self.admin = User.objects.create_user(username="admin_comisiones")
        self.admin.groups.add(grupo_admin)

    def _iniciar_sesion(self, usuario):
        self.client.force_login(usuario)
        session = self.client.session
        session["oidc_id_token_expiration"] = time.time() + 3600
        session.save()

    def test_listado_requiere_rol_administrador(self):
        """Un cliente no puede entrar a configurar comisiones."""
        grupo_cliente, _ = Group.objects.get_or_create(name="cliente")
        cliente = User.objects.create_user(username="un_cliente")
        cliente.groups.add(grupo_cliente)
        self._iniciar_sesion(cliente)

        respuesta = self.client.get(reverse('listar_segmentos'))
        self.assertEqual(respuesta.status_code, 403)

    def test_crear_segmento_valido(self):
        SegmentoCliente.objects.all().delete()
        self._iniciar_sesion(self.admin)
        respuesta = self.client.post(reverse('crear_segmento'), {
            'nombre': 'Corporativo',
            'porcentaje_comision': '0.75',
            'descripcion': 'Empresas con volumen alto',
        })
        self.assertRedirects(respuesta, reverse('listar_segmentos'))
        self.assertEqual(SegmentoCliente.objects.count(), 1)

    def test_crear_rechaza_porcentaje_fuera_de_rango(self):
        """La vista no debe guardar un porcentaje imposible."""
        SegmentoCliente.objects.all().delete()
        self._iniciar_sesion(self.admin)
        respuesta = self.client.post(reverse('crear_segmento'), {
            'nombre': 'Imposible',
            'porcentaje_comision': '150',
        })
        self.assertEqual(SegmentoCliente.objects.count(), 0)
        self.assertEqual(respuesta.status_code, 200)  # vuelve al formulario

    def test_baja_es_logica(self):
        """Dar de baja marca inactivo, no borra la fila."""
        SegmentoCliente.objects.all().delete()
        self._iniciar_sesion(self.admin)
        segmento = SegmentoCliente.objects.create(nombre="VIP", porcentaje_comision=1)

        self.client.post(reverse('eliminar_segmento', args=[segmento.pk]))

        self.assertEqual(SegmentoCliente.objects.count(), 1)
        segmento.refresh_from_db()
        self.assertFalse(segmento.activo)


class SegmentoAsignadoAClienteTest(TestCase):
    """La relación entre el cliente y su segmento, que es de donde sale la comisión."""

    def setUp(self):
        SegmentoCliente.objects.all().delete()
        self.vip = SegmentoCliente.objects.create(nombre="VIP", porcentaje_comision="0.50")
        self.minorista = SegmentoCliente.objects.create(nombre="Minorista", porcentaje_comision="2.00")
        self.cliente = Cliente.objects.create(
            nombre="ACME S.A.", tipo=Cliente.Tipo.JURIDICA,
            direccion="Av. Siempre Viva 123", cuenta_acreditar="123",
            correo="acme@example.com",
        )

        grupo_admin, _ = Group.objects.get_or_create(name="administrador")
        self.admin = User.objects.create_user(username="admin_asigna")
        self.admin.groups.add(grupo_admin)
        self.client.force_login(self.admin)
        session = self.client.session
        session["oidc_id_token_expiration"] = time.time() + 3600
        session.save()

    def test_cliente_sin_segmento_no_tiene_comision(self):
        self.assertIsNone(self.cliente.porcentaje_comision)

    def test_cliente_con_segmento_hereda_su_porcentaje(self):
        self.cliente.segmento = self.vip
        self.cliente.save()
        self.assertEqual(self.cliente.porcentaje_comision, Decimal("0.50"))

    def test_el_porcentaje_siempre_es_decimal(self):
        """Sirve para multiplicar sin sorpresas cuando se calcule la comisión.

        Un segmento recién creado con una cadena la conserva hasta que va y
        vuelve de la base. Si el porcentaje saliera como cadena,
        ``monto * porcentaje`` la repetiría en vez de multiplicar.
        """
        self.cliente.segmento = self.vip
        self.assertIsInstance(self.cliente.porcentaje_comision, Decimal)
        self.assertEqual(Decimal("100") * self.cliente.porcentaje_comision, Decimal("50.00"))

    def test_asignar_segmento_desde_la_pantalla(self):
        self.client.post(reverse('asignar_segmentos'), {
            f'segmento_{self.cliente.pk}': self.vip.pk,
        })
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.segmento, self.vip)

    def test_quitar_el_segmento_de_un_cliente(self):
        self.cliente.segmento = self.vip
        self.cliente.save()

        self.client.post(reverse('asignar_segmentos'), {f'segmento_{self.cliente.pk}': ''})

        self.cliente.refresh_from_db()
        self.assertIsNone(self.cliente.segmento)

    def test_ignora_un_segmento_inexistente(self):
        """El servidor no confía en lo que manda el navegador."""
        self.client.post(reverse('asignar_segmentos'), {
            f'segmento_{self.cliente.pk}': '99999',
        })
        self.cliente.refresh_from_db()
        self.assertIsNone(self.cliente.segmento)

    def test_ignora_un_segmento_dado_de_baja(self):
        self.minorista.activo = False
        self.minorista.save()

        self.client.post(reverse('asignar_segmentos'), {
            f'segmento_{self.cliente.pk}': self.minorista.pk,
        })

        self.cliente.refresh_from_db()
        self.assertIsNone(self.cliente.segmento)

    def test_no_se_puede_borrar_un_segmento_en_uso(self):
        """on_delete=PROTECT: borrarlo dejaría al cliente sin comisión válida."""
        self.cliente.segmento = self.vip
        self.cliente.save()
        with self.assertRaises(ProtectedError):
            self.vip.delete()

    def test_el_listado_cuenta_los_clientes_de_cada_segmento(self):
        self.cliente.segmento = self.vip
        self.cliente.save()

        respuesta = self.client.get(reverse('listar_segmentos'))
        conteos = {s.nombre: s.cantidad_clientes for s in respuesta.context['segmentos']}
        self.assertEqual(conteos["VIP"], 1)
        self.assertEqual(conteos["Minorista"], 0)


class ClienteApiSegmentoTest(TestCase):
    """La API de clientes expone y acepta el segmento sin romper lo anterior."""

    def setUp(self):
        SegmentoCliente.objects.all().delete()
        self.vip = SegmentoCliente.objects.create(nombre="VIP", porcentaje_comision="0.50")
        grupo_admin, _ = Group.objects.get_or_create(name="administrador")
        self.admin = User.objects.create_user(username="admin_api")
        self.admin.groups.add(grupo_admin)
        self.client.force_login(self.admin)
        session = self.client.session
        session["oidc_id_token_expiration"] = time.time() + 3600
        session.save()

    def test_crear_cliente_sin_segmento_sigue_funcionando(self):
        """Los campos nuevos son opcionales: la maqueta actual no los manda."""
        respuesta = self.client.post(
            reverse('clientes_lista'),
            data=json.dumps({
                "nombre": "ACME", "tipo": "Jurídica", "direccion": "Calle 1",
                "cuentaAcreditar": "123", "correo": "a@b.com",
            }),
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 201)
        self.assertIsNone(respuesta.json()["segmento"])
        self.assertIsNone(respuesta.json()["porcentajeComision"])

    def test_crear_cliente_con_segmento(self):
        respuesta = self.client.post(
            reverse('clientes_lista'),
            data=json.dumps({
                "nombre": "ACME", "tipo": "Jurídica", "direccion": "Calle 1",
                "cuentaAcreditar": "123", "correo": "a@b.com",
                "segmento": self.vip.pk,
            }),
            content_type="application/json",
        )
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.json()["segmento"], self.vip.pk)
        self.assertEqual(respuesta.json()["porcentajeComision"], "0.50")
