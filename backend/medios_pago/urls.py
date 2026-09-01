from django.urls import path
from . import views

urlpatterns = [
    path('', views.listar_medios_pago, name='listar_medios_pago'),
    path('crear/', views.crear_medio_pago, name='crear_medio_pago'),
    path('editar/<int:pk>/', views.editar_medio_pago, name='editar_medio_pago'),
    path('eliminar/<int:pk>/', views.eliminar_medio_pago, name='eliminar_medio_pago'),
]