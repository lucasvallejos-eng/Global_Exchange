"""Pruebas del historial de transacciones, solo consulta (IS2GE-70)."""
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth.models import Group
from django.urls import reverse

from clientes.models import Cliente

from . import servicios
from . import tests as base
from .models import Transaccion

ASUNCION = ZoneInfo("America/Asuncion")


class BaseHistorialTest(base.BaseOperacionesTest):
    """Dos clientes, cada uno con su usuario, y operaciones de los dos."""

    def setUp(self):
        super().setUp()
        self.otro_cliente = Cliente.objects.create(
            nombre="Otra Empresa S.A.", tipo=Cliente.Tipo.JURIDICA,
            direccion="Asunción", cuenta_acreditar="002", correo="otra@example.com",
        )
        self.otro_cliente.usuarios.add(self.otro_usuario)

        self.compra = self.crear(Transaccion.Tipo.COMPRA, "100")
        self.venta = servicios.pagar(self.crear(Transaccion.Tipo.VENTA, "50"), self.usuario)
        self.ajena = servicios.crear_operacion(
            self.otro_usuario, self.otro_cliente, Transaccion.Tipo.COMPRA, self.usd, Decimal("10")
        )

    def con_rol(self, nombre_usuario, rol):
        usuario, _ = base.Usuario.objects.get_or_create(username=nombre_usuario)
        usuario.groups.add(Group.objects.get_or_create(name=rol)[0])
        return usuario

    def fechar(self, transaccion, anio, mes, dia):
        Transaccion.objects.filter(pk=transaccion.pk).update(
            fecha_creacion=datetime(anio, mes, dia, 12, 0, tzinfo=ASUNCION)
        )


class QuienVeQueTest(BaseHistorialTest):
    """Cada uno ve lo que puede ver."""

    def test_el_cliente_ve_solo_las_de_sus_clientes(self):
        visibles = set(servicios.transacciones_visibles(self.usuario))
        self.assertEqual(visibles, {self.compra, self.venta})

    def test_analista_administrador_y_cajero_ven_todas(self):
        for rol in ("analista_cambiario", "administrador", "cajero"):
            usuario = self.con_rol(f"u_{rol}", rol)
            self.assertEqual(servicios.transacciones_visibles(usuario).count(), 3, rol)

    def test_sin_clientes_asociados_no_ve_ninguna(self):
        sin_clientes = self.con_rol("nadie", "cliente")
        self.assertFalse(servicios.transacciones_visibles(sin_clientes).exists())


class FiltrosTest(BaseHistorialTest):
    """Los filtros del historial."""

    def filtrar(self, **filtros):
        todas = servicios.transacciones_visibles(self.con_rol("analista", "analista_cambiario"))
        return set(servicios.filtrar_historial(todas, **filtros))

    def test_por_estado(self):
        self.assertEqual(self.filtrar(estado="PAGADA"), {self.venta})

    def test_por_tipo(self):
        self.assertEqual(self.filtrar(tipo="VENTA"), {self.venta})

    def test_por_moneda(self):
        self.assertEqual(len(self.filtrar(moneda="USD")), 3)
        self.assertEqual(self.filtrar(moneda="EUR"), set())

    def test_por_cliente(self):
        self.assertEqual(self.filtrar(cliente=self.otro_cliente.pk), {self.ajena})

    def test_por_rango_de_fechas_incluye_los_extremos(self):
        self.fechar(self.compra, 2026, 9, 1)
        self.fechar(self.venta, 2026, 9, 15)
        self.fechar(self.ajena, 2026, 9, 30)
        self.assertEqual(
            self.filtrar(desde=datetime(2026, 9, 1).date(), hasta=datetime(2026, 9, 15).date()),
            {self.compra, self.venta},
        )

    def test_un_valor_desconocido_no_filtra(self):
        self.assertEqual(len(self.filtrar(estado="INVENTADO", tipo="OTRO")), 3)


class PantallaHistorialTest(BaseHistorialTest):
    """La pantalla de Django."""

    def setUp(self):
        super().setUp()
        self.entrar(self.usuario)

    def historial(self, **parametros):
        return self.client.get(reverse("historial_operaciones"), parametros)

    def test_lista_solo_las_operaciones_propias(self):
        respuesta = self.historial()
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(set(respuesta.context["pagina"].object_list), {self.compra, self.venta})
        self.assertNotContains(respuesta, "Otra Empresa")

    def test_filtra_por_la_url(self):
        respuesta = self.historial(estado="PAGADA")
        self.assertEqual(list(respuesta.context["pagina"].object_list), [self.venta])

    def test_una_fecha_inexistente_se_ignora(self):
        respuesta = self.historial(desde="2026-02-31")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.context["pagina"].object_list), 2)

    def test_es_solo_consulta(self):
        respuesta = self.historial()
        self.assertNotContains(respuesta, 'method="post"')
        self.assertContains(respuesta, reverse("detalle_operacion", args=[self.compra.pk]))

    def test_pagina_y_conserva_los_filtros(self):
        for _ in range(25):
            self.crear(Transaccion.Tipo.COMPRA, "1")
        respuesta = self.historial(tipo="COMPRA")
        self.assertEqual(len(respuesta.context["pagina"].object_list), 20)
        self.assertContains(respuesta, "tipo=COMPRA&amp;pagina=2")

        segunda = self.historial(tipo="COMPRA", pagina=2)
        # 26 compras propias en total: 20 en la primera página, 6 en la segunda.
        self.assertEqual(len(segunda.context["pagina"].object_list), 6)

    def test_sin_resultados_lo_dice(self):
        self.assertContains(self.historial(moneda="EUR"), "Ninguna operación coincide")

    def test_el_menu_tiene_el_historial(self):
        self.assertContains(self.historial(), f'href="{reverse("historial_operaciones")}"')


class ApiHistorialTest(BaseHistorialTest):
    """El historial en JSON, para la maqueta."""

    def setUp(self):
        super().setUp()
        self.entrar(self.usuario)

    def test_devuelve_solo_las_propias(self):
        datos = self.client.get(reverse("api_operaciones")).json()
        self.assertEqual(datos["total"], 2)
        self.assertEqual({o["id"] for o in datos["operaciones"]}, {self.compra.pk, self.venta.pk})

    def test_acepta_los_mismos_filtros(self):
        datos = self.client.get(reverse("api_operaciones"), {"estado": "PAGADA"}).json()
        self.assertEqual([o["id"] for o in datos["operaciones"]], [self.venta.pk])

    def test_el_analista_ve_todas(self):
        self.entrar(self.con_rol("analista", "analista_cambiario"))
        self.assertEqual(self.client.get(reverse("api_operaciones")).json()["total"], 3)
