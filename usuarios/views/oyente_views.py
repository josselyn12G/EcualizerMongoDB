from django.views import View
from django.shortcuts import render
from usuarios.mixins import RequiereOyente
from catalogo.spotify_service import get_tendencias, get_novedades, get_para_ti, get_explorar


class ParaTiView(RequiereOyente, View):
    def get(self, request):
        tracks = get_para_ti(limit=20)
        return render(request, 'usuarios/oyente/para_ti.html', {
            'tracks': tracks,
        })


class ExplorarView(RequiereOyente, View):
    def get(self, request):
        categorias = get_explorar(limit=18)
        return render(request, 'usuarios/oyente/explorar.html', {
            'categorias': categorias,
        })


class TendenciasView(RequiereOyente, View):
    def get(self, request):
        tracks = get_tendencias(limit=20)
        return render(request, 'usuarios/oyente/tendencias.html', {
            'tracks': tracks,
        })


class NovedadesView(RequiereOyente, View):
    def get(self, request):
        albumes = get_novedades(limit=18)
        return render(request, 'usuarios/oyente/novedades.html', {
            'albumes': albumes,
        })