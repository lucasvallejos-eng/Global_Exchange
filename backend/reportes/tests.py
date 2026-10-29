"""Pruebas de los reportes de transacciones y ganancias."""
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth.models import Group
from django.urls import reverse

from clientes.models import Cliente
from cotizaciones.models import Cotizacion
from monedas.models import Moneda
from operaciones import servicios as operaciones
from operaciones import tests as base
from operaciones.models import Transaccion

from . import servicio

ASUNCION = ZoneInfo("America/Asuncion")


class BaseReportesTest(base.BaseOperacionesTest):
    """USD a 7300 / 7400 (precio medio 7350), descuento 5 % y comisión 1 %."""

    def pagada(self, tipo=Transaccion.Tipo.COMPRA, monto="100", dia=None, **extra):
        transaccion = operaciones.pagar(self.crear(tipo, monto, **extra), self.usuario)
        if dia:
            Transaccion.objects.filter(pk=transaccion.pk).update(
                fecha_pago=datetime(2026, 10, dia, 12, 0, tzinfo=ASUNCION)
            )
            transaccion.refresh_from_db()
        return transaccion

    def con_rol(self, rol):
        usuario = base.Usuario.objects.create_user(username=f"u_{rol}")
        usuario.groups.add(Group.objects.get_or_create(name=rol)[0])
        return usuario


class GananciaTest(BaseReportesTest):
    """Qué gana la casa con cada operación."""

    def test_compra_suma_comision_y_margen_sobre_el_precio_medio(self):
        # Vendió 100 USD a 7030 con el precio medio en 7350: perdió 320 por dólar.
        ganancia = servicio.ganancia_de(self.pagada(Transaccion.Tipo.COMPRA))
        self.assertEqual(ganancia["comision"], Decimal("7030"))
        self.assertEqual(ganancia["margen"], Decimal("-32000"))
        self.assertEqual(ganancia["total"], Decimal("-24970"))

    def test_venta_gana_lo_que_pago_por_debajo_del_precio_medio(self):
        # Compró 100 USD a 7300: 50 por dólar por debajo del medio.
        ganancia = servicio.ganancia_de(self.pagada(Transaccion.Tipo.VENTA))
        self.assertEqual(ganancia["comision"], Decimal("7300"))
        self.assertEqual(ganancia["margen"], Decimal("5000"))
        self.assertEqual(ganancia["total"], Decimal("12300"))

    def test_sin_descuento_la_compra_gana_medio_spread(self):
        self.cliente.segmento = None
        self.cliente.save()
        ganancia = servicio.ganancia_de(self.pagada(Transaccion.Tipo.COMPRA))
        self.assertEqual(ganancia, {"comision": Decimal("0"), "margen": Decimal("5000"),
                                    "total": Decimal("5000")})

    def test_sin_cotizacion_enlazada_el_margen_es_cero(self):
        transaccion = self.pagada()
        transaccion.cotizacion = None
        self.assertEqual(servicio.margen_de_cambio(transaccion), Decimal("0"))


class PagadasTest(BaseReportesTest):
    """Qué operaciones entran en los reportes."""

    def test_solo_cuentan_las_pagadas(self):
        pagada = self.pagada()
        self.crear()  # pendiente
        operaciones.cancelar(self.crear(), self.usuario)
        self.assertEqual(list(servicio.pagadas()), [pagada])

    def test_filtra_por_fecha_de_pago_con_los_extremos_incluidos(self):
        del_5 = self.pagada(dia=5)
        del_8 = self.pagada(dia=8)
        self.pagada(dia=12)
        entre = servicio.pagadas(desde=date(2026, 10, 5), hasta=date(2026, 10, 8))
        self.assertEqual(set(entre), {del_5, del_8})

    def test_filtra_por_tipo_moneda_y_cliente(self):
        compra = self.pagada(Transaccion.Tipo.COMPRA)
        venta = self.pagada(Transaccion.Tipo.VENTA)
        self.assertEqual(list(servicio.pagadas(tipo="VENTA")), [venta])
        self.assertEqual(set(servicio.pagadas(moneda="USD")), {compra, venta})
        self.assertFalse(servicio.pagadas(moneda="EUR").exists())
        self.assertEqual(set(servicio.pagadas(cliente=self.cliente.pk)), {compra, venta})
        self.assertFalse(servicio.pagadas(cliente=self.cliente.pk + 1).exists())
        # Un tipo que no existe no filtra.
        self.assertEqual(servicio.pagadas(tipo="OTRO").count(), 2)


class ResumenTest(BaseReportesTest):
    """Los números del tablero."""

    def setUp(self):
        super().setUp()
        self.pagada(Transaccion.Tipo.COMPRA, dia=5)   # ganancia -24.970
        self.pagada(Transaccion.Tipo.VENTA, dia=5)    # ganancia  12.300
        self.pagada(Transaccion.Tipo.VENTA, dia=8)    # ganancia  12.300
        self.resumen = servicio.resumen(servicio.pagadas())

    def test_totales(self):
        totales = self.resumen["totales"]
        self.assertEqual(totales["operaciones"], 3)
        self.assertEqual(totales["volumen"], Decimal("703000") + 2 * Decimal("730000"))
        self.assertEqual(totales["comisiones"], Decimal("7030") + 2 * Decimal("7300"))
        self.assertEqual(totales["margen"], Decimal("-32000") + 2 * Decimal("5000"))
        self.assertEqual(totales["ganancia"], totales["comisiones"] + totales["margen"])

    def test_por_tipo(self):
        self.assertEqual(self.resumen["por_tipo"]["COMPRA"]["ganancia"], Decimal("-24970"))
        self.assertEqual(self.resumen["por_tipo"]["VENTA"]["ganancia"], Decimal("24600"))
        self.assertEqual(self.resumen["por_tipo"]["VENTA"]["operaciones"], 2)

    def test_por_moneda_de_mayor_a_menor_ganancia(self):
        euro = Moneda.objects.create(codigo="EUR", nombre="Euro", simbolo="€")
        Cotizacion.objects.create(moneda=euro, precio_compra=Decimal("7900"), precio_venta=Decimal("8100"))
        operaciones.pagar(
            operaciones.crear_operacion(self.usuario, self.cliente, "VENTA", euro, Decimal("100")),
            self.usuario,
        )
        por_moneda = servicio.resumen(servicio.pagadas())["por_moneda"]
        self.assertEqual([fila["codigo"] for fila in por_moneda], ["EUR", "USD"])
        self.assertEqual(por_moneda[0]["monto_divisa"], Decimal("100"))
        self.assertEqual(por_moneda[1]["monto_divisa"], Decimal("300"))

    def test_por_dia_rellena_los_dias_sin_operaciones(self):
        serie = self.resumen["por_dia"]
        self.assertEqual([fila["fecha"].day for fila in serie], [5, 6, 7, 8])
        self.assertEqual([fila["operaciones"] for fila in serie], [2, 0, 0, 1])
        self.assertEqual(serie[0]["ganancia"], Decimal("-12670"))
        self.assertEqual(serie[1]["ganancia"], Decimal("0"))

    def test_la_serie_respeta_el_rango_pedido(self):
        serie = servicio.resumen(
            servicio.pagadas(), desde=date(2026, 10, 4), hasta=date(2026, 10, 9)
        )["por_dia"]
        self.assertEqual((serie[0]["fecha"].day, serie[-1]["fecha"].day, len(serie)), (4, 9, 6))

    def test_sin_operaciones(self):
        vacio = servicio.resumen(servicio.pagadas(moneda="EUR"))
        self.assertEqual(vacio["totales"]["operaciones"], 0)
        self.assertEqual(vacio["por_dia"], [])
        self.assertEqual(vacio["por_moneda"], [])


class ApiTest(BaseReportesTest):
    """Quién puede ver los reportes y qué devuelven."""

    def setUp(self):
        super().setUp()
        otro = Cliente.objects.create(
            nombre="Otra Empresa S.A.", tipo=Cliente.Tipo.JURIDICA, direccion="Asunción",
            cuenta_acreditar="002", correo="otra@example.com",
        )
        otro.usuarios.add(self.otro_usuario)
        self.pagada(Transaccion.Tipo.COMPRA, dia=5)
        self.pagada(Transaccion.Tipo.VENTA, dia=8)
        operaciones.pagar(
            operaciones.crear_operacion(self.otro_usuario, otro, "VENTA", self.usd, Decimal("10")),
            self.otro_usuario,
        )

    def test_el_cliente_y_el_cajero_no_ven_ganancias(self):
        for usuario in (self.usuario, self.con_rol("cajero")):
            self.entrar(usuario)
            for ruta in ("api_reportes_transacciones", "api_reportes_ganancias", "api_reportes_exportar"):
                self.assertEqual(self.client.get(reverse(ruta)).status_code, 403, ruta)

    def test_analista_y_administrador_ven_las_de_todos_los_clientes(self):
        for rol in ("analista_cambiario", "administrador"):
            self.entrar(self.con_rol(rol))
            datos = self.client.get(reverse("api_reportes_transacciones")).json()
            self.assertEqual(datos["totales"]["operaciones"], 3, rol)
            self.assertEqual({fila["cliente"] for fila in datos["operaciones"]},
                             {"Clara Cliente", "Otra Empresa S.A."})

    def test_cada_fila_trae_su_ganancia(self):
        self.entrar(self.con_rol("analista_cambiario"))
        datos = self.client.get(reverse("api_reportes_transacciones"), {"tipo": "COMPRA"}).json()
        (fila,) = datos["operaciones"]
        self.assertEqual((fila["comision"], fila["margen"], fila["ganancia"]), (7030, -32000, -24970))
        self.assertEqual(datos["totales"]["ganancia"], -24970)

    def test_tablero_de_ganancias(self):
        self.entrar(self.con_rol("analista_cambiario"))
        datos = self.client.get(
            reverse("api_reportes_ganancias"), {"desde": "2026-10-05", "hasta": "2026-10-08"}
        ).json()
        self.assertEqual(datos["totales"]["operaciones"], 2)
        self.assertEqual(datos["porTipo"]["VENTA"]["ganancia"], 12300)
        self.assertEqual(datos["porMoneda"][0]["moneda"], "USD")
        self.assertEqual([dia["fecha"] for dia in datos["porDia"]],
                         ["2026-10-05", "2026-10-06", "2026-10-07", "2026-10-08"])

    def test_exporta_el_reporte_en_csv(self):
        self.entrar(self.con_rol("administrador"))
        respuesta = self.client.get(reverse("api_reportes_exportar"), {"tipo": "COMPRA"})
        self.assertEqual(respuesta["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("reporte-transacciones.csv", respuesta["Content-Disposition"])
        lineas = respuesta.content.decode("utf-8-sig").splitlines()
        self.assertEqual(len(lineas), 2)  # encabezado + la compra
        self.assertTrue(lineas[0].startswith("Operación;Fecha de pago;Cliente"))
        self.assertIn("Clara Cliente;Compra de divisa;USD;100.00", lineas[1])
        self.assertIn(";7030;-32000;-24970;", lineas[1])
