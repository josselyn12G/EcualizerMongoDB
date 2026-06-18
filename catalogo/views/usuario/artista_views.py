"""
Vistas de Artistas para el USUARIO (oyente).

Listado de todos los artistas registrados en Ecualizer con su foto
extraída de Deezer y un álbum destacado por cada uno.
"""

from django.views.generic import View
from django.shortcuts import render, get_object_or_404
from django.db import DatabaseError

from usuarios.mixins import RequiereOyente
from usuarios.models import Artista
from ...models import Album
from ...services import (
    sp_listar_albumes,
    deezer_get_artist_image,
    deezer_enrich_albumes,
)
from biblioteca.services import (
    get_artistas_seguidos_ids,
    is_artista_seguido,
    get_albumes_guardados_ids,
)


class UsuarioArtistaListView(RequiereOyente, View):
    template_name = 'catalogo/usuario/usuario_artista.html'

    def get(self, request):
        busqueda = (request.GET.get('q') or '').strip()

        qs = Artista.objects.all().order_by('nombre_artistico')
        if busqueda:
            qs = qs.filter(nombre_artistico__icontains=busqueda)

        artistas = []
        for a in qs[:60]:
            artistas.append({
                'pk': a.pk,
                'nombre': a.nombre_artistico,
                'biografia': a.biografia or '',
                'foto': deezer_get_artist_image(a.nombre_artistico),
            })

        # Artista destacado para el hero (el primero)
        destacado = artistas[0] if artistas else None

        followed_ids = set()
        try:
            followed_ids = get_artistas_seguidos_ids(request.session['usuario_id'])
        except DatabaseError:
            pass

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
        artista = get_object_or_404(Artista, pk=pk)
        foto = deezer_get_artist_image(artista.nombre_artistico)

        # Álbumes del artista (vía SP filtrando por artista_id)
        try:
            albumes = sp_listar_albumes(
                artista_id=artista.pk,
                estado='activo',
                busqueda=None,
            )
        except DatabaseError:
            # Fallback al ORM si el SP falla
            albumes = []
            for alb in Album.objects.filter(artista_id=artista.pk,
                                            estado_album='activo'):
                albumes.append({
                    'idAlbum': alb.pk,
                    'tituloAlbum': alb.titulo_album,
                    'fechaLanzamientoAlbum': alb.fecha_lanzamiento_album,
                    'nombreArtistico': artista.nombre_artistico,
                })
        deezer_enrich_albumes(albumes)

        uid = request.session['usuario_id']
        seguido = False
        saved_ids = set()
        try:
            seguido = is_artista_seguido(uid, artista.pk)
            saved_ids = get_albumes_guardados_ids(uid)
        except DatabaseError:
            pass

        return render(request, self.template_name, {
            'artista': artista,
            'foto': foto,
            'albumes': albumes,
            'total_albumes': len(albumes),
            'modo': 'detail',
            'artista_seguido': seguido,
            'saved_ids': saved_ids,
        })
