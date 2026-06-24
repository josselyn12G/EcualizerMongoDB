"""
Vistas de Cancion para el USUARIO (oyente).

Migradas a MongoDB: listar, filtrar por género, detalle, preview.
"""

from django.views.generic import View
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseBadRequest

from usuarios.mixins import RequiereOyente
from ...services import (
    deezer_enrich_canciones,
    deezer_get_artist_image,
    deezer_get_album_image,
    deezer_get_track_image,
    deezer_get_track_preview,
    obtener_letra,
)
from ...services.cancion_mongo import (
    listar_canciones,
    filtrar_canciones_genero,
    listar_generos_disponibles,
    get_cancion_ns,
    registrar_reproduccion,
)
from biblioteca.mongo_service import get_canciones_liked_ids, is_cancion_liked


# ──────────────────────────────────────────────────────────
# LIST · todas las canciones activas
# ──────────────────────────────────────────────────────────
class UsuarioCancionListView(RequiereOyente, View):
    template_name = 'catalogo/usuario/usuario_cancion.html'

    def get(self, request):
        busqueda = request.GET.get('q') or None

        try:
            canciones = listar_canciones(estado='activa', busqueda=busqueda)
        except Exception:
            canciones = []

        # Las carátulas se cargan en el cliente (lazy) para no bloquear el
        # render con llamadas a la API de imágenes.
        featured_artist = canciones[0].get('nombreArtistico') if canciones else None

        liked_ids = set()
        try:
            liked_ids = get_canciones_liked_ids(request.session.get('usuario_id'))
        except Exception:
            pass

        return render(request, self.template_name, {
            'canciones': canciones,
            'generos': listar_generos_disponibles(),
            'busqueda': busqueda or '',
            'genero_actual': '',
            'modo': 'list',
            'featured_artist': featured_artist,
            'liked_ids': liked_ids,
        })


# ──────────────────────────────────────────────────────────
# FILTER · por género musical (nombre de género como str)
# ──────────────────────────────────────────────────────────
class UsuarioCancionFilterView(RequiereOyente, View):
    template_name = 'catalogo/usuario/usuario_cancion.html'

    def get(self, request, nombre_genero):
        try:
            canciones = filtrar_canciones_genero(nombre_genero)
        except Exception:
            canciones = []

        featured_artist = nombre_genero
        if canciones:
            featured_artist = canciones[0].get('nombreArtistico') or nombre_genero

        liked_ids = set()
        try:
            liked_ids = get_canciones_liked_ids(request.session.get('usuario_id'))
        except Exception:
            pass

        return render(request, self.template_name, {
            'canciones': canciones,
            'generos': listar_generos_disponibles(),
            'busqueda': '',
            'genero_actual': nombre_genero,
            'genero_nombre': nombre_genero,
            'featured_artist': featured_artist,
            'modo': 'filter',
            'liked_ids': liked_ids,
        })


# ──────────────────────────────────────────────────────────
# DETAIL · ficha + registra reproducción al hacer "play"
# ──────────────────────────────────────────────────────────
class UsuarioCancionDetailView(RequiereOyente, View):
    template_name = 'catalogo/usuario/usuario_cancion.html'

    def get(self, request, pk):
        cancion = get_cancion_ns(pk)
        if not cancion or getattr(cancion, 'estado_cancion', None) != 'activa':
            return redirect('catalogo:usuario_cancion_list')

        # Las 3 llamadas a APIs externas (2 imágenes + letra) son independientes:
        # se ejecutan en paralelo para que el detalle cargue más rápido.
        from concurrent.futures import ThreadPoolExecutor
        artista_nom = cancion.album.artista.nombre_artistico or ''
        album_tit = cancion.album.titulo_album or ''
        cancion_nom = cancion.nombre_cancion or ''
        with ThreadPoolExecutor(max_workers=3) as _pool:
            f_cover = _pool.submit(deezer_get_album_image, album_tit, artista_nom)
            f_artist = _pool.submit(deezer_get_artist_image, artista_nom)
            f_letra = _pool.submit(obtener_letra, artista_nom, cancion_nom)
            cover = f_cover.result()
            artist_image = f_artist.result()
            letra_api = f_letra.result()
        letra_db = (cancion.letra_cancion or '').strip()
        letra = letra_api or letra_db or ''

        liked = False
        try:
            liked = is_cancion_liked(request.session.get('usuario_id'), pk)
        except Exception:
            pass

        return render(request, self.template_name, {
            'cancion': cancion,
            'cover_url': cover,
            'artist_image': artist_image,
            'letra': letra,
            'letra_origen': 'api' if letra_api else ('db' if letra_db else None),
            'letra_api': letra_api or '',
            'letra_db': letra_db,
            'generos': listar_generos_disponibles(),
            'modo': 'detail',
            'cancion_liked': liked,
        })

    def post(self, request, pk):
        cancion = get_cancion_ns(pk)
        if not cancion or getattr(cancion, 'estado_cancion', None) != 'activa':
            return JsonResponse({'ok': False, 'error': 'canción no encontrada'}, status=404)

        usuario_id = request.session.get('usuario_id')
        pais = request.POST.get('pais', 'Ecuador')
        try:
            duracion = int(request.POST.get('duracion_escuchada', cancion.duracion or 0))
        except (ValueError, TypeError):
            return HttpResponseBadRequest('duracion_escuchada inválido')
        fue_saltada = request.POST.get('fue_saltada', 'N')

        try:
            resultado = registrar_reproduccion(
                usuario_id=usuario_id,
                cancion_id=pk,
                pais=pais,
                duracion_escuchada=duracion,
                fue_saltada=fue_saltada,
            )
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=400)

        return JsonResponse({'ok': True, 'data': resultado})


# ──────────────────────────────────────────────────────────
# PREVIEW · resuelve la URL MP3 de Deezer (~30 s) on-demand
# ──────────────────────────────────────────────────────────
class UsuarioCancionPreviewView(RequiereOyente, View):
    """GET /catalogo/canciones/<pk>/preview/ → {ok, preview, cover, title, artist}"""

    def get(self, request, pk):
        cancion = get_cancion_ns(pk)
        if not cancion or getattr(cancion, 'estado_cancion', None) != 'activa':
            return JsonResponse({'ok': False, 'error': 'no encontrada'}, status=404)

        preview = deezer_get_track_preview(
            cancion.nombre_cancion or '',
            cancion.album.artista.nombre_artistico or '',
        )
        cover = deezer_get_track_image(
            cancion.nombre_cancion or '',
            cancion.album.artista.nombre_artistico or '',
            cancion.album.titulo_album or '',
        )
        return JsonResponse({
            'ok': bool(preview),
            'preview': preview or '',
            'cover': cover,
            'title': cancion.nombre_cancion,
            'artist': cancion.album.artista.nombre_artistico,
        })
