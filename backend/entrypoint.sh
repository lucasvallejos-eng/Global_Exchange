#!/bin/sh
# Arranque del contenedor de producción: aplica las migraciones pendientes y
# levanta gunicorn. Así, actualizar el sistema es reconstruir la imagen y
# reiniciar: la base queda al día sola.
set -e

python manage.py migrate --noinput

# Pocos procesos a propósito: la base es SQLite, que admite un solo escritor
# a la vez. Para el uso del proyecto alcanza; si creciera, el paso natural es
# pasar a PostgreSQL (ver docs/despliegue-produccion.md).
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-2}" \
    --access-logfile -
