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


Índices
-------

* :ref:`genindex`
* :ref:`modindex`