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
    deezer_enrich_artistas,
)
from ...services.catalogo_mongo import listar_albumes
from biblioteca.mongo_service import (
    get_artistas_seguidos_ids, is_artista_seguido, get_albumes_guardados_ids,
)


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
            })
        # Las fotos se cargan en el cliente (lazy) para no bloquear el render.

        destacado = artistas[0] if artistas else None

        try:
            followed_ids = get_artistas_seguidos_ids(request.session.get('usuario_id'))
        except Exception:
            followed_ids = set()

        return render(request, self.template_name, {
            'artistas': artistas,
            'destacado': destacado,
            'busqueda': busqueda,
            'modo': 'list',
            'followed_ids': followed_ids,
        })


class UsuarioArtistaDetailView(RequiereOyente, View):
    template_name = 'catalogo/usuario/usuario_artista.html'

    def get(self, request, pk):
        artista = admin_get_user(pk, tipo='artista')
        if not artista:
            return redirect('catalogo:usuario_artista_list')

        nombre = getattr(artista, 'nombre_artistico', '') or ''

        try:
            albumes = listar_albumes(artista_id=pk, estado='activo')
        except Exception:
            albumes = []
        # Foto del artista y carátulas de álbumes → lazy-load en el cliente.

        uid = request.session.get('usuario_id')
        try:
            artista_seguido = is_artista_seguido(uid, pk)
        except Exception:
            artista_seguido = False
        try:
            saved_ids = get_albumes_guardados_ids(uid)
        except Exception:
            saved_ids = set()

        return render(request, self.template_name, {
            'artista': artista,
            'albumes': albumes,
            'total_albumes': len(albumes),
            'modo': 'detail',
            'artista_seguido': artista_seguido,
            'saved_ids': saved_ids,
        })
