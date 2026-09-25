from django.urls import path
from . import views

urlpatterns = [
    path('transacciones/<int:pk>/pagar/', views.procesar_pago, name='procesar_pago'),
]