from django.urls import path
from . import views

urlpatterns = [
    path('', views.listar_monedas, name='listar_monedas'),
    path('crear/', views.crear_moneda, name='crear_moneda'),
    path('editar/<int:pk>/', views.editar_moneda, name='editar_moneda'),
    path('eliminar/<int:pk>/', views.eliminar_moneda, name='eliminar_moneda'),
]