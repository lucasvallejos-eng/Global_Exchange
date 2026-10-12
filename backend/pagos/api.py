"""API de pagos para la maqueta."""
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from . import servicio


@require_GET
@login_required
def configuracion(request):
    """La clave publicable de Stripe (la usa Stripe.js en el navegador).

    La maqueta la pide acá en vez de tenerla en su propio .env: así las
    claves de Stripe viven en un solo lugar (backend/.env.stripe).
    """
    return JsonResponse({
        "habilitado": servicio.habilitado(),
        "publishableKey": settings.STRIPE_PUBLISHABLE_KEY,
    })
