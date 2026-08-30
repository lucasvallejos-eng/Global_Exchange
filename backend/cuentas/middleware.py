"""
CORS mínimo para que la maqueta (React en otro puerto) pueda llamar a la API
del backend (localhost:8000) enviando la cookie de sesión.

Solo aplica a rutas /api/ y solo permite el origen de la maqueta. No usamos una
librería externa: alcanza con reflejar estos encabezados a mano.
"""
from django.conf import settings
from django.http import HttpResponse


class CorsMaquetaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.origen = settings.MAQUETA_URL.rstrip("/")

    def __call__(self, request):
        if request.method == "OPTIONS" and request.path.startswith("/api/"):
            respuesta = HttpResponse(status=204)
        else:
            respuesta = self.get_response(request)

        if request.path.startswith("/api/"):
            respuesta["Access-Control-Allow-Origin"] = self.origen
            respuesta["Access-Control-Allow-Credentials"] = "true"
            respuesta["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
            respuesta["Access-Control-Allow-Headers"] = "Content-Type, X-CSRFToken"
            respuesta["Vary"] = "Origin"

        return respuesta
