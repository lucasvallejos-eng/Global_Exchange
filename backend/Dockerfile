# Imagen de producción del backend: Django servido por gunicorn.
# Se usa desde docker-compose.prod.yml; ver docs/despliegue-produccion.md.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Primero solo las dependencias: si el código cambia pero ellas no, Docker
# reutiliza esta capa y la reconstrucción tarda segundos en vez de minutos.
COPY requirements.txt requirements-produccion.txt ./
RUN pip install --no-cache-dir -r requirements-produccion.txt

COPY . .

# Si el repo se clonó en Windows, el script puede venir con fin de línea CRLF,
# que sh no entiende. Se normaliza acá por las dudas.
RUN sed -i 's/\r$//' entrypoint.sh

# Junta los estáticos para WhiteNoise. collectstatic exige una SECRET_KEY
# aunque no la use: se le da una de descarte solo para este paso.
RUN DJANGO_DEBUG=0 DJANGO_SECRET_KEY=solo-para-collectstatic python manage.py collectstatic --noinput

EXPOSE 8000
ENTRYPOINT ["sh", "./entrypoint.sh"]
