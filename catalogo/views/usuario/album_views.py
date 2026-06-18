"""
Vistas de Album para el USUARIO (oyente).

El oyente solo lee — nunca modifica.

SPs usados:
  - Catalogo.SP_ListarAlbumes  → UsuarioAlbumListView · solo activos
"""

from django.views.generic import View
from django.shortcuts import render, get_object_or_404
from django.db import DatabaseError

from usuarios.mixins import RequiereOyente
from ...models import Album
from ...services import (
    sp_listar_albumes,
    deezer_enrich_albumes,
    deezer_get_album_image,
    deezer_get_artist_image,
)
from biblioteca.services import (
    get_albumes_guardados_ids,
    is_album_guardado,
    get_canciones_liked_ids,
)


def _enriquecer_canciones_modelo(canciones_qs, cover_url):
    """Convierte canciones-modelo a dicts simples y agrega la portada heredada del álbum."""
    out = []
    for c in canciones_qs:
        out.append({
            'pk': c.pk,
            'numero_pista': c.numero_pista,
            'nombre_cancion': c.nombre_cancion,
            'duracion': c.duracion,
            'duracion_formateada': c.duracion_formateada,
            'calidad_kbps': c.calidad_kbps,
            'total_reproducciones': c.total_reproducciones,
            'coverUrl': cover_url,
        })
    return out


# ──────────────────────────────────────────────────────────
# LIST · álbumes activos
# ──────────────────────────────────────────────────────────
class UsuarioAlbumListView(RequiereOyente, View):
    template_name = 'catalogo/usuario/usuario_album.html'

    def get(self, request):
        busqueda = request.GET.get('q') or None
        try:
            albumes = sp_listar_albumes(
                artista_id=None, estado='activo', busqueda=busqueda,
            )
        except DatabaseError:
            albumes = []
        deezer_enrich_albumes(albumes)

        saved_ids = set()
        try:
            saved_ids = get_albumes_guardados_ids(request.session['usuario_id'])
        except DatabaseError:
            pass

        return render(request, self.template_name, {
            'albumes': albumes,
            'busqueda': busqueda or '',
            'modo': 'list',
            'saved_ids': saved_ids,
        })


# ──────────────────────────────────────────────────────────
# DETAIL · vista inline (NO abre ventana nueva)
# ──────────────────────────────────────────────────────────
class UsuarioAlbumDetailView(RequiereOyente, View):
    template_name = 'catalogo/usuario/usuario_album.html'

    def get(self, request, pk):
        album = get_object_or_404(
            Album.objects.select_related('artista', 'tipo_album'),
            pk=pk,
            estado_album='activo',
        )

        cover_url = deezer_get_album_image(
            album.titulo_album,
            album.artista.nombre_artistico,
        )
        artist_image = deezer_get_artist_image(album.artista.nombre_artistico)

        canciones_qs = (
            album.canciones
            .filter(estado_cancion='activa')
            .order_by('numero_pista')
        )
        canciones = _enriquecer_canciones_modelo(canciones_qs, cover_url)

        # Duración total aproximada en minutos
        total_seg = sum(c['duracion'] for c in canciones)
        total_min = round(total_seg / 60)

        uid = request.session['usuario_id']
        saved = False
        liked_ids = set()
        try:
            saved = is_album_guardado(uid, album.pk)
            liked_ids = get_canciones_liked_ids(uid)
        except DatabaseError:
            pass

        return render(request, self.template_name, {
            'album': album,
            'canciones': canciones,
            'cover_url': cover_url,
            'artist_image': artist_image,
            'total_canciones': len(canciones),
            'duracion_total_min': total_min,
            'modo': 'detail',
            'album_guardado': saved,
            'liked_ids': liked_ids,
        })


# ──────────────────────────────────────────────────────────
# SEARCH
# ──────────────────────────────────────────────────────────
class UsuarioAlbumSearchView(RequiereOyente, View):
    template_name = 'catalogo/usuario/usuario_album.html'

    def get(self, request):
        q = request.GET.get('q', '').strip()
        try:
            resultados = sp_listar_albumes(
                artista_id=None, estado='activo',
                busqueda=q if q else None,
            )
        except DatabaseError:
            resultados = []
        deezer_enrich_albumes(resultados)

        return render(request, self.template_name, {
            'albumes': resultados,
            'busqueda': q,
            'modo': 'search',
            'es_busqueda': True,
        })
