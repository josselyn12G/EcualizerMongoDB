"""
Vistas de favoritos / social para el OYENTE.

- POST endpoints de toggle (devuelven JSON con el nuevo estado).
- Vistas de lista: "Canciones que me gustan", "Mis Artistas", "Mis Álbumes".
- CRUD de Playlists y gestión de canciones dentro de cada una.
"""

import logging

from django.views import View
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseBadRequest

from usuarios.mixins import RequiereOyente
from catalogo.services import (
    deezer_get_artist_image,
    deezer_get_track_image,
    deezer_enrich_albumes,
    deezer_enrich_artistas,
)

from . import mongo_service as ms

logger = logging.getLogger('ecualizer.biblioteca')


# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────
def _uid(request):
    return request.session.get('usuario_id')


def _ajax_ok(active: bool, **extra) -> JsonResponse:
    return JsonResponse({'ok': True, 'active': active, **extra})


def _ajax_err(msg: str) -> JsonResponse:
    return JsonResponse({'ok': False, 'error': msg}, status=400)


# ══════════════════════════════════════════════════════════
# TOGGLES (POST → JSON)
# ══════════════════════════════════════════════════════════
class ToggleLikeCancionView(RequiereOyente, View):
    def post(self, request, pk):
        usuario_id = _uid(request)
        try:
            active = ms.toggle_like_cancion(usuario_id, pk)
            logger.info('LIKE cancion=%s usuario=%s → %s', pk, usuario_id, active)
            return _ajax_ok(active, kind='like_cancion', target_id=pk)
        except Exception as e:
            logger.error('Error toggle_like_cancion: %s', e)
            return _ajax_err(str(e))

    def get(self, request, pk):
        return HttpResponseBadRequest('Use POST')


class ToggleSeguirArtistaView(RequiereOyente, View):
    def post(self, request, pk):
        usuario_id = _uid(request)
        try:
            active = ms.toggle_seguir_artista(usuario_id, pk)
            logger.info('FOLLOW artista=%s usuario=%s → %s', pk, usuario_id, active)
            return _ajax_ok(active, kind='seguir_artista', target_id=pk)
        except Exception as e:
            logger.error('Error toggle_seguir_artista: %s', e)
            return _ajax_err(str(e))

    def get(self, request, pk):
        return HttpResponseBadRequest('Use POST')


class ToggleGuardarAlbumView(RequiereOyente, View):
    def post(self, request, pk):
        usuario_id = _uid(request)
        try:
            active = ms.toggle_guardar_album(usuario_id, pk)
            logger.info('SAVE album=%s usuario=%s → %s', pk, usuario_id, active)
            return _ajax_ok(active, kind='guardar_album', target_id=pk)
        except Exception as e:
            logger.error('Error toggle_guardar_album: %s', e)
            return _ajax_err(str(e))

    def get(self, request, pk):
        return HttpResponseBadRequest('Use POST')


# ══════════════════════════════════════════════════════════
# LISTAS — Canciones que me gustan / Mis Artistas / Mis Álbumes
# ══════════════════════════════════════════════════════════
class MisCancionesLikedView(RequiereOyente, View):
    template_name = 'biblioteca/mis_canciones_liked.html'

    def get(self, request):
        usuario_id = _uid(request)
        try:
            canciones = ms.get_canciones_liked(usuario_id)
        except Exception as e:
            logger.error('Error cargando canciones liked: %s', e)
            canciones = []

        for c in canciones:
            c['coverUrl'] = deezer_get_track_image(
                c.get('nombreCancion') or '',
                c.get('nombreArtistico') or '',
                c.get('tituloAlbum') or '',
            )

        return render(request, self.template_name, {
            'canciones': canciones,
            'total': len(canciones),
        })


class MisArtistasSeguidosView(RequiereOyente, View):
    template_name = 'biblioteca/mis_artistas.html'

    def get(self, request):
        usuario_id = _uid(request)
        try:
            artistas = ms.get_artistas_seguidos(usuario_id)
        except Exception as e:
            logger.error('Error cargando artistas seguidos: %s', e)
            artistas = []

        deezer_enrich_artistas(artistas, name_key='nombreArtistico', image_key='foto')

        return render(request, self.template_name, {
            'artistas': artistas,
            'total': len(artistas),
        })


class MisAlbumesGuardadosView(RequiereOyente, View):
    template_name = 'biblioteca/mis_albumes.html'

    def get(self, request):
        usuario_id = _uid(request)
        try:
            albumes = ms.get_albumes_guardados(usuario_id)
        except Exception as e:
            logger.error('Error cargando albumes guardados: %s', e)
            albumes = []

        deezer_enrich_albumes(albumes)

        return render(request, self.template_name, {
            'albumes': albumes,
            'total': len(albumes),
        })


# ══════════════════════════════════════════════════════════
# PLAYLISTS (MongoDB)
# ══════════════════════════════════════════════════════════
class MisPlaylistsView(RequiereOyente, View):
    template_name = 'biblioteca/playlist_list.html'

    def get(self, request):
        usuario_id = _uid(request)
        try:
            playlists = ms.listar_playlists(usuario_id)
        except Exception as e:
            logger.error('Error cargando playlists: %s', e)
            playlists = []
        return render(request, self.template_name, {
            'playlists': playlists,
            'total': len(playlists),
        })


class CrearPlaylistView(RequiereOyente, View):
    template_name = 'biblioteca/playlist_form.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        usuario_id = _uid(request)
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        visibilidad = request.POST.get('visibilidad', 'Privada')
        tipo = request.POST.get('tipo', 'Personal')

        if not nombre:
            return render(request, self.template_name, {
                'error': 'El nombre es obligatorio.'
            })

        try:
            ms.crear_playlist(usuario_id, nombre, descripcion, visibilidad, tipo)
        except Exception as e:
            logger.error('Error creando playlist: %s', e)
            return render(request, self.template_name, {
                'error': f'Error: {str(e)}'
            })

        return redirect('biblioteca:mis_playlists')


class DetallePlaylistView(RequiereOyente, View):
    template_name = 'biblioteca/playlist_detail.html'

    def get(self, request, pk):
        usuario_id = _uid(request)
        try:
            playlist = ms.get_playlist_info(pk, usuario_id)
            if not playlist:
                return redirect('biblioteca:mis_playlists')
            canciones = ms.get_canciones_playlist(pk)
        except Exception as e:
            logger.error('Error cargando playlist: %s', e)
            playlist = None
            canciones = []

        # Catálogo de canciones disponibles para agregar (MongoDB)
        try:
            from catalogo.services.cancion_mongo import listar_canciones
            todas_canciones = listar_canciones(estado='activa')
        except Exception:
            todas_canciones = []

        return render(request, self.template_name, {
            'playlist': playlist,
            'canciones': canciones,
            'total': len(canciones),
            'todas_canciones': todas_canciones,
        })


class EditarPlaylistView(RequiereOyente, View):
    template_name = 'biblioteca/playlist_edit.html'

    def get(self, request, pk):
        usuario_id = _uid(request)
        try:
            playlist = ms.get_playlist_info(pk, usuario_id)
            if not playlist:
                return redirect('biblioteca:mis_playlists')
        except Exception as e:
            logger.error('Error cargando playlist: %s', e)
            return redirect('biblioteca:mis_playlists')
        return render(request, self.template_name, {'playlist': playlist})

    def post(self, request, pk):
        usuario_id = _uid(request)
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        visibilidad = request.POST.get('visibilidad', 'Privada')

        if not nombre:
            playlist = ms.get_playlist_info(pk, usuario_id)
            return render(request, self.template_name, {
                'playlist': playlist,
                'error': 'El nombre es obligatorio.'
            })

        try:
            ms.actualizar_playlist(pk, usuario_id, nombre, descripcion, visibilidad)
        except Exception as e:
            logger.error('Error editando playlist: %s', e)
            playlist = ms.get_playlist_info(pk, usuario_id)
            return render(request, self.template_name, {
                'playlist': playlist,
                'error': f'No se pudo actualizar: {str(e)}'
            })

        return redirect('biblioteca:detalle_playlist', pk=pk)


class EliminarPlaylistView(RequiereOyente, View):

    def post(self, request, pk):
        usuario_id = _uid(request)
        try:
            ms.eliminar_playlist(pk, usuario_id)
        except Exception as e:
            logger.error('Error eliminando playlist: %s', e)
        return redirect('biblioteca:mis_playlists')


class AgregarCancionPlaylistView(RequiereOyente, View):

    def post(self, request, pk):
        usuario_id = _uid(request)
        cancion_id = request.POST.get('cancion_id')

        if not cancion_id:
            return redirect('biblioteca:detalle_playlist', pk=pk)

        try:
            ms.agregar_cancion_playlist(pk, usuario_id, cancion_id)
        except Exception as e:
            logger.error('Error agregando cancion a playlist: %s', e)

        return redirect('biblioteca:detalle_playlist', pk=pk)


class EliminarCancionPlaylistView(RequiereOyente, View):

    def post(self, request, pk, cancion_pk):
        usuario_id = _uid(request)
        try:
            ms.quitar_cancion_playlist(pk, usuario_id, cancion_pk)
        except Exception as e:
            logger.error('Error eliminando cancion de playlist: %s', e)
        return redirect('biblioteca:detalle_playlist', pk=pk)
