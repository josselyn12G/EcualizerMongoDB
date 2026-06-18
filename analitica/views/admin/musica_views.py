"""Vistas de Analítica · Música, Álbumes, Géneros, Artistas."""

from django.shortcuts import render
from django.views import View

from usuarios.mixins import RequiereAdmin
from ... import services
from ...forms import PeriodoForm


class MusicaView(RequiereAdmin, View):
    """Top canciones (likes + ranking global)."""
    template_name = 'analitica/admin/musica.html'

    def get(self, request):
        form = PeriodoForm(request.GET or None)
        periodo = (form.is_valid() and form.cleaned_data.get('periodo')) or 'mes'
        return render(request, self.template_name, {
            'form':      form,
            'periodo':   periodo,
            'top_likes': services.top_canciones_likes(20),
            'ranking':   services.ranking_global_canciones(periodo),
        })


class AlbumesView(RequiereAdmin, View):
    template_name = 'analitica/admin/albumes.html'

    def get(self, request):
        return render(request, self.template_name, {
            'mas_guardados': services.albumes_mas_guardados(20),
        })


class GenerosView(RequiereAdmin, View):
    template_name = 'analitica/admin/generos.html'

    def get(self, request):
        return render(request, self.template_name, {
            'top_generos': services.top_generos(15),
        })


class ArtistasView(RequiereAdmin, View):
    template_name = 'analitica/admin/artistas.html'

    def get(self, request):
        return render(request, self.template_name, {
            'top_artistas': services.top_artistas(20),
        })
