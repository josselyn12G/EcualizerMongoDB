"""URL configuration for ecualizer_config project."""
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render


def home(request):
    """Página inicial pública."""
    return render(request, 'home.html')


urlpatterns = [
    # ── Páginas públicas ──────────────────────────────────────────────
    path('', home, name='home'),

    # ── Apps de Ecualizer ─────────────────────────────────────────────
    path('usuarios/',   include('usuarios.urls')),
    path('catalogo/',   include('catalogo.urls')),
    path('biblioteca/', include('biblioteca.urls')),
    path('pagos/',      include('pagos.urls')),

    # ── Analítica e Industria (van antes de admin/) ───────────────────
    path('admin/analitica/', include('analitica.urls')),
    path('admin/industria/', include('industria.urls')),

    # ── Django admin built-in (último) ───────────────────────────────
    path('admin/', admin.site.urls),
]