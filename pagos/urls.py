from django.urls import path
from .views import HistorialSuscripcionesView

app_name = 'pagos'

urlpatterns = [
    path('suscripciones/', HistorialSuscripcionesView.as_view(), name='historial'),
]