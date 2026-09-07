"""Vistas de la API de Clientes (CRUD) y del listado de usuarios asociables."""
import json

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from cuentas.decorators import rol_requerido

from .models import Cliente


def _cliente_a_dict(cliente):
    """Convierte una instancia de Cliente en un diccionario serializable a JSON."""
    return {
        "id": cliente.id,
        "nombre": cliente.nombre,
        "tipo": cliente.tipo,
        "direccion": cliente.direccion,
        "cuentaAcreditar": cliente.cuenta_acreditar,
        "correo": cliente.correo,
        "usuarios": list(cliente.usuarios.values_list("id", flat=True)),
    }


def _body_json(request):
    """Parsea el cuerpo de la request como JSON; devuelve un dict vacío si falla."""
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return {}


@login_required
@require_http_methods(["GET", "POST"])
@csrf_protect
def clientes_lista(request):
    """
    Lista todos los clientes (GET) o crea uno nuevo (POST).

    GET no requiere rol especial, cualquier usuario autenticado puede
    consultar el listado. La creación (POST) delega en
    :func:`_crear_cliente`, que sí exige rol de administrador.
    """
    if request.method == "GET":
        clientes = Cliente.objects.prefetch_related("usuarios").all()
        return JsonResponse([_cliente_a_dict(c) for c in clientes], safe=False)

    return _crear_cliente(request)


@rol_requerido("administrador")
def _crear_cliente(request):
    """
    Crea un nuevo cliente a partir de los datos recibidos en el body (JSON).

    Requiere rol de administrador. Asocia además la lista de usuarios
    indicada en el campo ``usuarios`` del payload.
    """
    datos = _body_json(request)
    cliente = Cliente.objects.create(
        nombre=datos.get("nombre", ""),
        tipo=datos.get("tipo", Cliente.Tipo.FISICA),
        direccion=datos.get("direccion", ""),
        cuenta_acreditar=datos.get("cuentaAcreditar", ""),
        correo=datos.get("correo", ""),
    )
    cliente.usuarios.set(datos.get("usuarios", []))
    return JsonResponse(_cliente_a_dict(cliente), status=201)


@login_required
@require_http_methods(["GET", "PATCH", "DELETE"])
@csrf_protect
def clientes_detalle(request, pk):
    """
    Obtiene (GET), actualiza (PATCH) o elimina (DELETE) un cliente puntual.

    Devuelve 404 si no existe un cliente con el ``pk`` indicado.
    PATCH y DELETE requieren rol de administrador (ver
    :func:`_actualizar_cliente` y :func:`_borrar_cliente`).
    """
    try:
        cliente = Cliente.objects.get(pk=pk)
    except Cliente.DoesNotExist:
        return JsonResponse({"detail": "No encontrado."}, status=404)

    if request.method == "GET":
        return JsonResponse(_cliente_a_dict(cliente))
    if request.method == "PATCH":
        return _actualizar_cliente(request, cliente)
    return _borrar_cliente(request, cliente)


@rol_requerido("administrador")
def _actualizar_cliente(request, cliente):
    """
    Actualiza parcialmente los campos de un cliente (PATCH).

    Solo modifica los campos presentes en el body; el resto queda
    sin cambios. Si el body incluye ``usuarios``, reemplaza la
    asociación completa de usuarios del cliente.
    """
    datos = _body_json(request)
    for campo, atributo in (
        ("nombre", "nombre"),
        ("tipo", "tipo"),
        ("direccion", "direccion"),
        ("cuentaAcreditar", "cuenta_acreditar"),
        ("correo", "correo"),
    ):
        if campo in datos:
            setattr(cliente, atributo, datos[campo])
    cliente.save()
    if "usuarios" in datos:
        cliente.usuarios.set(datos["usuarios"])
    return JsonResponse(_cliente_a_dict(cliente))


@rol_requerido("administrador")
def _borrar_cliente(request, cliente):
    """Elimina un cliente de la base de datos. Requiere rol de administrador."""
    cliente.delete()
    return JsonResponse({}, status=204)


@login_required
def usuarios_lista(request):
    """Usuarios que se pueden asociar como 'usuarios asociados' de una empresa."""
    User = get_user_model()
    usuarios = User.objects.all().order_by("username")
    data = [
        {
            "id": u.id,
            "username": u.username,
            "nombre": u.get_full_name() or u.username,
            "email": u.email,
        }
        for u in usuarios
    ]
    return JsonResponse(data, safe=False)