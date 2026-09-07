"""Filtro de plantilla para preguntar por el rol del usuario.

Las plantillas no pueden llamar a ``user.groups.filter(...)`` porque el motor
de plantillas de Django no permite pasarle argumentos a un método. Este filtro
resuelve eso para poder esconder del menú los enlaces que el usuario no tiene
permitido abrir.

Es solo para la presentación: el control de acceso de verdad lo hace
``rol_requerido`` en el servidor. Esconder un enlace no protege nada.

Uso::

    {% load roles %}
    {% if user|tiene_rol:"administrador" %}...{% endif %}
"""
from django import template

register = template.Library()


@register.filter
def tiene_rol(usuario, nombre_rol):
    """Devuelve True si el usuario pertenece al grupo ``nombre_rol``."""
    if not usuario or not usuario.is_authenticated:
        return False
    return usuario.groups.filter(name=nombre_rol).exists()
