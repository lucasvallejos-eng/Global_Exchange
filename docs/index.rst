Documentación de Global Exchange
================================

Global Exchange es una casa de cambio digital: compra y venta de divisas, con
operativa web y operativa presencial en ventanilla.

Esta documentación se genera con Sphinx a partir de los *docstrings* del código
del backend. Para regenerarla, desde ``Global_Exchange/docs``::

   ..\backend\.venv\Scripts\python -m sphinx -b html . _build/html

El resultado queda en ``docs/_build/html/index.html``.

.. toctree::
   :maxdepth: 2
   :caption: Contenido


Autenticación y roles
---------------------

La autenticación está delegada en Keycloak (OIDC). Django no guarda ni procesa
contraseñas en ningún momento (RN05): los formularios de credenciales los dibuja
Keycloak. Los roles llegan en el token y se mapean a grupos de Django, que es
donde se validan del lado del servidor.

.. automodule:: cuentas.auth
   :members:
   :undoc-members:

.. automodule:: cuentas.decorators
   :members:
   :undoc-members:

.. automodule:: cuentas.middleware
   :members:
   :undoc-members:

.. automodule:: cuentas.views
   :members:


Clientes
--------

.. automodule:: clientes.models
   :members:
   :undoc-members:

.. automodule:: clientes.views
   :members:
   :undoc-members:


Monedas
-------

.. automodule:: monedas.models
   :members:
   :undoc-members:

.. automodule:: monedas.views
   :members:

.. automodule:: monedas.api
   :members:
   :undoc-members:


Cotizaciones y Auditoría
------------------------

El modelo hace cumplir RN10 (la tasa de compra siempre menor que la de venta)
desde ``Cotizacion.clean()``. Las vistas y la API llaman a ``full_clean()`` antes de
guardar.

Reglas de Negocio de Auditoría:
* **Historial de cambios:** Se registra automáticamente un evento en ``HistorialCotizacion`` almacenando el usuario administrador, los precios anteriores y los nuevos precios asignados.

.. automodule:: cotizaciones.models
   :members:
   

.. automodule:: cotizaciones.views
   :members:
   

.. automodule:: cotizaciones.api
   :members:
   

.. automodule:: cotizaciones.admin
   :members:
   


Medios de pago
--------------

.. automodule:: medios_pago.models
   :members:
   

.. automodule:: medios_pago.views
   :members:

.. automodule:: medios_pago.api
   :members:
   


Comisiones por segmento de cliente
----------------------------------

Administración de la configuración de porcentajes de comisión y los descuentos aplicados a operaciones de compra por cada segmento de cliente (Minorista, Mayorista, VIP).

Cada cliente hace referencia a su segmento a través de ``Cliente.segmento`` para consultar tanto el porcentaje de comisión como el descuento de compra aplicable.

.. automodule:: comisiones.models
   :members:
   

.. automodule:: comisiones.views
   :members:
   

.. automodule:: comisiones.api
   :members:
   


Tasas y simulador
-----------------

.. automodule:: tasas.views
   :members:



Operaciones de compra y venta
-----------------------------

El alcance del Sprint 3: la operación de compra o venta con su cálculo de
comisión y tasa aplicada, y la cancelación automática cuando la cotización
cambia antes del pago. Las reglas viven en ``operaciones.servicios``; las
pantallas de Django y la API de la maqueta solo las llaman.

.. automodule:: operaciones.models
   :members:

.. automodule:: operaciones.servicios
   :members:

.. automodule:: operaciones.views
   :members:

.. automodule:: operaciones.api
   :members:


Caja (operativa presencial)
---------------------------

Apertura con arqueo por denominaciones, compra y venta en ventanilla, cierre
con la diferencia entre el saldo teórico y el contado, e historial de cajas.
El arqueo sigue también la moneda local (``Moneda.es_local``): las ventas en
efectivo suman guaraníes al cajón y las compras los restan; lo cobrado con
tarjeta no pasa por el cajón. Solo el rol ``cajero`` opera la caja.

.. automodule:: caja.models
   :members:

.. automodule:: caja.api
   :members:


Pagos con tarjeta (Stripe)
--------------------------

Cobros con tarjeta en modo test. Las tarjetas se cargan con Stripe Elements:
el número y el CVV van directo a Stripe y nunca pasan por este backend, que
solo guarda el id del ``PaymentMethod``, la marca, los últimos 4 dígitos y el
vencimiento. Ver ``docs/integracion-stripe.md``.

.. automodule:: pagos.models
   :members:

.. automodule:: pagos.servicio
   :members:

.. automodule:: pagos.api
   :members:


Facturación electrónica (Factura Segura)
----------------------------------------

Cada operación pagada genera su factura electrónica a nombre del **cliente**
(no del usuario que la cargó). La emite y la firma Factura Segura, que es
quien habla con el SIFEN de la DNIT; el sistema guarda el número, el CDC y el
estado, y permite descargar el KuDE (PDF) y el XML firmado.

La cátedra asignó pocos números de factura, así que por defecto **no se emite
nada**: las facturas quedan simuladas hasta que se prende
``FACTURA_SEGURA_EMITIR``. Ver ``docs/integracion-factura-segura.md``.

.. automodule:: facturacion.models
   :members:

.. automodule:: facturacion.servicio
   :members:

.. automodule:: facturacion.senales
   :members:

.. automodule:: facturacion.api
   :members:

.. automodule:: facturacion.views
   :members:


Reportes y tablero de ganancias
-------------------------------

Reportes de las operaciones pagadas y de lo que gana la casa con cada una (la
comisión más el margen de cambio sobre el precio medio de la cotización). Solo
los ven el administrador y el analista cambiario. El reporte de transacciones
se puede exportar a CSV.

.. automodule:: reportes.servicio
   :members:

.. automodule:: reportes.api
   :members:


Notificaciones
--------------

La campanita de la web avisa las compras y ventas exitosas (con el medio de
pago y el valor), las fallidas (tarjeta rechazada, 3D Secure no aprobado,
cotización que cambió antes del pago o cancelada por el usuario) y los
cambios de cotización (a todos los usuarios menos a quien la cambió). En la
caja se avisa al cajero y, si se cobró con tarjeta, al dueño de la tarjeta.
La maqueta consulta ``/api/notificaciones/`` cada 15 segundos y después de
cada operación.

Cada usuario elige qué recibir (``PreferenciaNotificaciones``): compras,
ventas y cambios de cotización, combinados como quiera, y en las cotizaciones
solo algunas divisas si lo prefiere. Sin preferencias guardadas recibe todo.

.. automodule:: notificaciones.models
   :members:

.. automodule:: notificaciones.servicio
   :members:

.. automodule:: notificaciones.senales
   :members:

.. automodule:: notificaciones.api
   :members:

Índices
-------

* :ref:`genindex`
* :ref:`modindex`