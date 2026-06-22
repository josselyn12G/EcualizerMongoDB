from django.urls import path
from .views import HistorialSuscripcionesView, PagoSuscripcionView

app_name = 'pagos'

urlpatterns = [
    path('suscripciones/', HistorialSuscripcionesView.as_view(), name='historial'),
    path('suscripciones/pagar/<str:plan_id>/', PagoSuscripcionView.as_view(), name='pagar'),
]