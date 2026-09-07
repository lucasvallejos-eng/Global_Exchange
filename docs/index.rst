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


Cotizaciones
------------

El modelo hace cumplir RN10 (la tasa de compra siempre menor que la de venta)
desde ``Cotizacion.clean()``. Las vistas llaman a ``full_clean()`` antes de
guardar, porque ``objects.create()`` no dispara esa validación.

.. automodule:: cotizaciones.models
   :members:
   :undoc-members:

.. automodule:: cotizaciones.views
   :members:
   :undoc-members:


Medios de pago
--------------

.. automodule:: medios_pago.models
   :members:
   :undoc-members:

.. automodule:: medios_pago.views
   :members:
   :undoc-members:


Comisiones por segmento de cliente
----------------------------------

Acá vive solo la *configuración* de los porcentajes y la asignación de un
segmento a cada cliente. El cálculo de la comisión sobre una operación de
compra o venta corresponde al Sprint 3, y se apoya en
``Cliente.porcentaje_comision``.

.. automodule:: comisiones.models
   :members:
   :undoc-members:

.. automodule:: comisiones.views
   :members:
   :undoc-members:


Tasas y simulador
-----------------

.. automodule:: tasas.views
   :members:
   :undoc-members:


Índices
-------

* :ref:`genindex`
* :ref:`modindex`
