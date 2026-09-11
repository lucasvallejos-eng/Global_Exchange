# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information


import os
import sys

import django

# El código a documentar vive en backend/, no en la raíz del repo.
sys.path.insert(0, os.path.abspath('../backend'))

# autodoc importa los módulos de verdad para leerles los docstrings, y un
# modelo de Django no se puede importar sin que Django esté configurado
# (revienta con ImproperlyConfigured). Por eso hay que arrancarlo acá antes
# de que Sphinx empiece a recorrer el código.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',  # agrega un enlace al código fuente en cada página
]

project = 'GlobalExchange'
copyright = '2026, lucasvallejos-eng'
author = 'lucasvallejos-eng'
release = '0.1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

# Ojo: acá había un segundo "extensions = []" que dejaba la lista de arriba en
# nada, así que autodoc quedaba apagado y no se generaba documentación del
# código. No volver a declarar extensions más de una vez.

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

language = 'es'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']

# --- Agregar esto a docs/conf.py ---

DJANGO_INTERNAL_DESCRIPTORS = {
    "DeferredAttribute",
    "ForwardManyToOneDescriptor",
    "ForwardOneToOneDescriptor",
    "ManyToManyDescriptor",
    "ReverseManyToOneDescriptor",
    "ReverseOneToOneDescriptor",
    "ManyToOneRel",
    "ManyToManyRel",
    "OneToOneRel",
    "cached_property",
}

DJANGO_INTERNAL_NAMES = {
    "DoesNotExist",
    "MultipleObjectsReturned",
}


def skip_django_internals(app, what, name, obj, skip, options):
    """
    Evita que autodoc documente los descriptores/excepciones internas
    de Django (en inglés) cuando no agregamos un docstring propio.
    """
    # Excepciones automáticas de cada modelo
    if name in DJANGO_INTERNAL_NAMES:
        return True

    # Descriptores de campos/relaciones (FK, M2M, etc.)
    if type(obj).__name__ in DJANGO_INTERNAL_DESCRIPTORS:
        return True

    return skip


def setup(app):
    app.connect("autodoc-skip-member", skip_django_internals)