from django.urls import path
from . import views

urlpatterns = [
    path('', views.listar_segmentos, name='listar_segmentos'),
    path('crear/', views.crear_segmento, name='crear_segmento'),
    path('asignar/', views.asignar_segmentos, name='asignar_segmentos'),
    path('editar/<int:pk>/', views.editar_segmento, name='editar_segmento'),
    path('eliminar/<int:pk>/', views.eliminar_segmento, name='eliminar_segmento'),
]
