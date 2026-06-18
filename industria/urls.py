"""URLs de la app industria — CRUD de Discográficas y Contratos."""

from django.urls import path
from . import views


app_name = 'industria'

urlpatterns = [
    # ── Discográficas ─────────────────────────────────
    path('discograficas/',
         views.DiscograficaListView.as_view(),
         name='discografica_list'),
    path('discograficas/nueva/',
         views.DiscograficaCreateView.as_view(),
         name='discografica_create'),
    path('discograficas/<int:pk>/editar/',
         views.DiscograficaUpdateView.as_view(),
         name='discografica_update'),
    path('discograficas/<int:pk>/eliminar/',
         views.DiscograficaDeleteView.as_view(),
         name='discografica_delete'),

    # ── Contratos ──────────────────────────────────────
    path('contratos/',
         views.ContratoListView.as_view(),
         name='contrato_list'),
    path('contratos/nuevo/',
         views.ContratoCreateView.as_view(),
         name='contrato_create'),
    path('contratos/<int:artista>/<int:disco>/<int:num>/editar/',
         views.ContratoUpdateView.as_view(),
         name='contrato_update'),
    path('contratos/<int:artista>/<int:disco>/<int:num>/eliminar/',
         views.ContratoDeleteView.as_view(),
         name='contrato_delete'),
]
