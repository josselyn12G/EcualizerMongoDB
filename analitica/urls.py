"""URLs del Dashboard de Analítica del Administrador."""

from django.urls import path

from . import views


app_name = 'analitica'

urlpatterns = [
    # ── Resumen general
    path('',                views.ResumenGeneralView.as_view(), name='resumen'),

    # ── Subsecciones de analítica
    path('musica/',         views.MusicaView.as_view(),         name='musica'),
    path('albumes/',        views.AlbumesView.as_view(),        name='albumes'),
    path('reproducciones/', views.ReproduccionesView.as_view(), name='reproducciones'),
    path('generos/',        views.GenerosView.as_view(),        name='generos'),
    path('artistas/',       views.ArtistasView.as_view(),       name='artistas'),
    path('actividad/',      views.ActividadView.as_view(),      name='actividad'),

    # ── Reportes y regalías
    path('reportes/',       views.ReportesView.as_view(),       name='reportes'),
    path('regalias/',       views.RegaliasView.as_view(),       name='regalias'),
    path('regalias/confirmar/',
         views.ConfirmarRegaliasView.as_view(),
         name='regalias_confirmar'),
    path('regalias/confirmar/todos/',
         views.ConfirmarRegaliasTodosView.as_view(),
         name='regalias_confirmar_todos'),

    # ── Comercial (lectura desde analítica)
    path('discograficas/',  views.DiscograficasView.as_view(),  name='discograficas'),
    path('contratos/',      views.ContratosView.as_view(),      name='contratos'),
    path('planes/',         views.PlanesView.as_view(),         name='planes'),
    path('suscripciones/',  views.SuscripcionesView.as_view(),  name='suscripciones'),

    # ── API
    path('api/kpis/',       views.KpisJsonView.as_view(),       name='api_kpis'),
]
