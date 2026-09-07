Módulo de Clientes
===================

Este módulo gestiona el CRUD de clientes (empresas) y su asociación con usuarios.

Modelos (models.py)
--------------------

.. autoclass:: clientes.models.Cliente
   :members:
   :show-inheritance:

Vistas (views.py)
------------------

.. autofunction:: clientes.views.clientes_lista

.. autofunction:: clientes.views.clientes_detalle

.. autofunction:: clientes.views.usuarios_lista