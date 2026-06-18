"""
Vistas de Cancion para el USUARIO (oyente).

SPs usados:
  - Catalogo.SP_ListarCanciones            → UsuarioCancionListView
  - Catalogo.SP_FiltrarCancionesGenero     → UsuarioCancionFilterView
  - Analitica.SP_RegistrarReproduccion     → UsuarioCancionDetailView (al reproducir)
"""

from django.views.generic import View
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.db import DatabaseError

from usuarios.mixins import RequiereOyente
from ...models import Cancion, GeneroMusical
from ...services import (
    sp_listar_canciones,
    sp_filtrar_canciones_genero,
    sp_registrar_reproduccion,
    deezer_enrich_canciones,
    deezer_get_artist_image,
    deezer_get_album_image,
    deezer_get_track_image,
    deezer_get_track_preview,
    obtener_letra,
)
from biblioteca.services import (
    get_canciones_liked_ids,
    is_cancion_liked,
)


# ──────────────────────────────────────────────────────────
# LIST · todas las canciones activas
# ──────────────────────────────────────────────────────────
class UsuarioCancionListView(RequiereOyente, View):
    template_name = 'catalogo/usuario/usuario_cancion.html'

    def get(self, request):
        busqueda = request.GET.get('q') or None

        try:
            canciones = sp_listar_canciones(
                artista_id=None, album_id=None,
                estado='activa', busqueda=busqueda,
            )
        except DatabaseError:
            canciones = []

        # Enriquecemos con portada de Deezer
        deezer_enrich_canciones(canciones)

        # Artista destacado (el de la primera canción) para el hero
        featured_artist = None
        featured_image = None
        if canciones:
            featured_artist = canciones[0].get('nombreArtistico') or 'Ecualizer'
            featured_image = deezer_get_artist_image(featured_artist)

        liked_ids = set()
        try:
            liked_ids = get_canciones_liked_ids(request.session['usuario_id'])
        except DatabaseError:
            pass

        return render(request, self.template_name, {
            'canciones': canciones,
            'generos': GeneroMusical.objects.all(),
            'busqueda': busqueda or '',
            'genero_actual': '',
            'modo': 'list',
            'featured_artist': featured_artist,
            'featured_image': featured_image,
            'liked_ids': liked_ids,
        })


# ──────────────────────────────────────────────────────────
# FILTER · por género musical
# ──────────────────────────────────────────────────────────
class UsuarioCancionFilterView(RequiereOyente, View):
    template_name = 'catalogo/usuario/usuario_cancion.html'

    def get(self, request, genero_id):
        try:
            canciones = sp_filtrar_canciones_genero(genero_id=genero_id)
        except DatabaseError:
            canciones = []
        deezer_enrich_canciones(canciones)

        genero = get_object_or_404(GeneroMusical, pk=genero_id)
        featured_image = None
        featured_artist = genero.nombre_genero
        if canciones:
            featured_artist = canciones[0].get('nombreArtistico') or genero.nombre_genero
            featured_image = deezer_get_artist_image(featured_artist)

        liked_ids = set()
        try:
            liked_ids = get_canciones_liked_ids(request.session['usuario_id'])
        except DatabaseError:
            pass

        return render(request, self.template_name, {
            'canciones': canciones,
            'generos': GeneroMusical.objects.all(),
            'busqueda': '',
            'genero_actual': genero_id,
            'genero_nombre': genero.nombre_genero,
            'featured_artist': featured_artist,
            'featured_image': featured_image,
            'modo': 'filter',
            'liked_ids': liked_ids,
        })


# ──────────────────────────────────────────────────────────
# DETAIL · ficha + (al hacer "play") registra reproducción
# ──────────────────────────────────────────────────────────
class UsuarioCancionDetailView(RequiereOyente, View):
    template_name = 'catalogo/usuario/usuario_cancion.html'

    def get(self, request, pk):
        cancion = get_object_or_404(
            Cancion.objects.select_related('album', 'album__artista'),
            pk=pk,
            estado_cancion='activa',
        )
        cover = deezer_get_album_image(
            cancion.album.titulo_album,
            cancion.album.artista.nombre_artistico,
        )
        artist_image = deezer_get_artist_image(
            cancion.album.artista.nombre_artistico,
        )

        # Letra: traemos AMBAS (api.lyrics.ovh + BD) para mostrarlas por
        # separado en el detalle. Mantenemos `letra`/`letra_origen` por
        # compatibilidad con el template antiguo.
        letra_api = obtener_letra(
            cancion.album.artista.nombre_artistico,
            cancion.nombre_cancion,
        )
        letra_db = (cancion.letra_cancion or '').strip()
        letra = letra_api or letra_db or ''

        liked = False
        try:
            liked = is_cancion_liked(request.session['usuario_id'], cancion.pk)
        except DatabaseError:
            pass

        return render(request, self.template_name, {
            'cancion': cancion,
            'cover_url': cover,
            'artist_image': artist_image,
            'letra': letra,
            'letra_origen': 'api' if letra_api else ('db' if letra_db else None),
            'letra_api': letra_api or '',
            'letra_db':  letra_db,
            'generos': GeneroMusical.objects.all(),
            'modo': 'detail',
            'cancion_liked': liked,
        })

    def post(self, request, pk):
        cancion = get_object_or_404(Cancion, pk=pk, estado_cancion='activa')
        usuario_id = request.session['usuario_id']
        pais = request.POST.get('pais', 'Ecuador')
        try:
            duracion = int(request.POST.get('duracion_escuchada', cancion.duracion))
        except ValueError:
            return HttpResponseBadRequest('duracion_escuchada inválido')
        fue_saltada = request.POST.get('fue_saltada', 'N')

        try:
            resultado = sp_registrar_reproduccion(
                usuario_id=usuario_id,
                cancion_id=cancion.pk,
                pais=pais,
                duracion_escuchada=duracion,
                fue_saltada=fue_saltada,
            )
        except DatabaseError as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=400)

        return JsonResponse({'ok': True, 'data': resultado})


# ──────────────────────────────────────────────────────────
# PREVIEW · resuelve la URL MP3 de Deezer (~30 s) on-demand
# ──────────────────────────────────────────────────────────
class UsuarioCancionPreviewView(RequiereOyente, View):
    """GET /catalogo/canciones/<pk>/preview/ → {ok, preview, cover, title, artist}"""

    def get(self, request, pk):
        cancion = get_object_or_404(
            Cancion.objects.select_related('album', 'album__artista'),
            pk=pk, estado_cancion='activa',
        )
        preview = deezer_get_track_preview(
            cancion.nombre_cancion,
            cancion.album.artista.nombre_artistico,
        )
        # Misma función que usa el listado (`deezer_enrich_canciones` →
        # `deezer_get_track_image`) para que la portada del player coincida
        # exactamente con la que se ve en la fila de "Popular".
        cover = deezer_get_track_image(
            cancion.nombre_cancion,
            cancion.album.artista.nombre_artistico,
            cancion.album.titulo_album,
        )
        return JsonResponse({
            'ok': bool(preview),
            'preview': preview or '',
            'cover': cover,
            'title': cancion.nombre_cancion,
            'artist': cancion.album.artista.nombre_artistico,
        })
