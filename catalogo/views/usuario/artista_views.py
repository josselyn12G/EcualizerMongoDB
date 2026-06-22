"""
Vistas de Artistas para el USUARIO (oyente) — migradas a MongoDB.
"""

from django.views.generic import View
from django.shortcuts import render, redirect

from usuarios.mixins import RequiereOyente
from usuarios.mongo_service import admin_list_users, admin_get_user
from ...services import (
    deezer_get_artist_image,
    deezer_enrich_albumes,
)
from ...services.catalogo_mongo import listar_albumes


class UsuarioArtistaListView(RequiereOyente, View):
    template_name = 'catalogo/usuario/usuario_artista.html'

    def get(self, request):
        busqueda = (request.GET.get('q') or '').strip()

        try:
            artistas_raw = admin_list_users('artista', q=busqueda)
        except Exception:
            artistas_raw = []

        artistas = []
        for a in artistas_raw[:60]:
            nombre = getattr(a, 'nombre_artistico', '') or ''
            artistas.append({
                'pk': getattr(a, 'pk', ''),
                'nombre': nombre,
                'biografia': getattr(a, 'biografia', '') or '',
                'foto': deezer_get_artist_image(nombre),
            })

        destacado = artistas[0] if artistas else None

        return render(request, self.template_name, {
            'artistas': artistas,
            'destacado': destacado,
            'busqueda': busqueda,
            'modo': 'list',
            'followed_ids': set(),
        })


class UsuarioArtistaDetailView(RequiereOyente, View):
    template_name = 'catalogo/usuario/usuario_artista.html'

    def get(self, request, pk):
        artista = admin_get_user(pk, tipo='artista')
        if not artista:
            return redirect('catalogo:usuario_artista_list')

        nombre = getattr(artista, 'nombre_artistico', '') or ''
        foto = deezer_get_artist_image(nombre)

        try:
            albumes = listar_albumes(artista_id=pk, estado='activo')
        except Exception:
            albumes = []
        deezer_enrich_albumes(albumes)

        return render(request, self.template_name, {
            'artista': artista,
            'foto': foto,
            'albumes': albumes,
            'total_albumes': len(albumes),
            'modo': 'detail',
            'artista_seguido': False,
            'saved_ids': set(),
        })
