from django.urls import path
from . import views

urlpatterns = [
    path('', views.listar_cotizaciones, name='listar_cotizaciones'),
    path('crear/', views.crear_cotizacion, name='crear_cotizacion'),
    path('editar/<int:pk>/', views.editar_cotizacion, name='editar_cotizacion'),
    path('eliminar/<int:pk>/', views.eliminar_cotizacion, name='eliminar_cotizacion'),
]