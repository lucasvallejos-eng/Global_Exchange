from django.urls import path
from . import views

urlpatterns = [
    path('', views.ver_tasas, name='ver_tasas'),
    path('simulador/', views.simulador, name='simulador'),
]
