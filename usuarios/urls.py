from django.urls import path
from . import views
from pagos.artista_views import ArtistaMonetizacionView
from pagos.admin_views import (
    AdminPlanesListView,
    AdminSuscripcionesListView,
    AdminPagosListView,
    AdminIngresosView,
)
from analitica.views.artista import AnalyticsArtistaView, MonetizacionArtistaView
from industria.views import ContratosArtistaView
from .views.oyente_views import ParaTiView, ExplorarView, TendenciasView, NovedadesView

urlpatterns = [
    path('', views.index_usuarios, name='index_usuarios'),

    # ── Autenticacion ──────────────────────────────────────────────────
    path('login/',        views.LoginView.as_view(),       name='login'),
    path('logout/',       views.LogoutView.as_view(),      name='logout'),
    path('admin/login/',  views.AdminLoginView.as_view(),  name='admin_login'),

    # ── Seleccion y registro ───────────────────────────────────────────
    path('registro/tipo/',          views.SeleccionarTipoView.as_view(), name='seleccionar_tipo'),
    path('registro/oyente/',        views.RegistroOyenteView.as_view(),  name='registro_oyente'),
    path('registro/artista/',       views.RegistroArtistaView.as_view(), name='registro_artista'),
    path('registro/administrador/', views.RegistroAdminView.as_view(),   name='registro_admin'),

    # ── Dashboards / perfiles ──────────────────────────────────────────
    path('perfil/oyente/',  views.DashboardOyenteView.as_view(),  name='dashboard_oyente'),
    path('oyente/perfil/',        views.PerfilOyenteView.as_view(),        name='perfil_oyente'),
    path('oyente/configuracion/', views.ConfiguracionOyenteView.as_view(), name='configuracion_oyente'),
    path('perfil/artista/', views.DashboardArtistaView.as_view(), name='dashboard_artista'),
    path('artista/perfil/',        views.PerfilArtistaView.as_view(),        name='perfil_artista'),
    path('artista/configuracion/', views.ConfiguracionArtistaView.as_view(), name='configuracion_artista'),
    path('perfil/artista/analytics/',
         AnalyticsArtistaView.as_view(),
         name='artista_analytics'),
    path('perfil/artista/monetizacion/',
         MonetizacionArtistaView.as_view(),
         name='artista_monetizacion'),
    path('perfil/artista/contratos/',
         ContratosArtistaView.as_view(),
         name='artista_contratos'),

    # ── Panel de administracion ────────────────────────────────────────
    path('admin/dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),

    # Oyentes
    path('admin/oyentes/',                   views.AdminOyenteListView.as_view(),   name='admin_oyente_list'),
    path('admin/oyentes/<int:pk>/',          views.AdminOyenteDetailView.as_view(), name='admin_oyente_detail'),
    path('admin/oyentes/<int:pk>/editar/',   views.AdminOyenteEditView.as_view(),   name='admin_oyente_edit'),
    path('admin/oyentes/<int:pk>/eliminar/', views.AdminOyenteDeleteView.as_view(), name='admin_oyente_delete'),

    # Artistas
    path('admin/artistas/',                   views.AdminArtistaListView.as_view(),   name='admin_artista_list'),
    path('admin/artistas/<int:pk>/',          views.AdminArtistaDetailView.as_view(), name='admin_artista_detail'),
    path('admin/artistas/<int:pk>/editar/',   views.AdminArtistaEditView.as_view(),   name='admin_artista_edit'),
    path('admin/artistas/<int:pk>/eliminar/', views.AdminArtistaDeleteView.as_view(), name='admin_artista_delete'),

    # Administradores
    path('admin/admins/',                   views.AdminAdminListView.as_view(),   name='admin_admin_list'),
    path('admin/admins/<int:pk>/',          views.AdminAdminDetailView.as_view(), name='admin_admin_detail'),
    path('admin/admins/<int:pk>/editar/',   views.AdminAdminEditView.as_view(),   name='admin_admin_edit'),
    path('admin/admins/<int:pk>/eliminar/', views.AdminAdminDeleteView.as_view(), name='admin_admin_delete'),

    # Personas
    path('admin/personas/',        views.AdminPersonaListView.as_view(),   name='admin_persona_list'),
    path('admin/personas/<int:pk>/', views.AdminPersonaDetailView.as_view(), name='admin_persona_detail'),

    # Comercial — Planes, Suscripciones, Pagos
    path('admin/comercial/planes/',        AdminPlanesListView.as_view(),        name='admin_planes_list'),
    path('admin/comercial/suscripciones/', AdminSuscripcionesListView.as_view(), name='admin_suscripciones_list'),
    path('admin/comercial/pagos/',         AdminPagosListView.as_view(),         name='admin_pagos_list'),

    # Analítica — Ingresos
    path('admin/analitica/ingresos/', AdminIngresosView.as_view(), name='admin_ingresos'),

    # Monetización Artista
    path('perfil/artista/monetizacion/', ArtistaMonetizacionView.as_view(), name='artista_monetizacion'),
    
    # Secciones oyente - Spotify
    path('oyente/para-ti/',    ParaTiView.as_view(),    name='para_ti'),
    path('oyente/explorar/',   ExplorarView.as_view(),   name='explorar'),
    path('oyente/tendencias/', TendenciasView.as_view(), name='tendencias'),
    path('oyente/novedades/',  NovedadesView.as_view(),  name='novedades'),
]