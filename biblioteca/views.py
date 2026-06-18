"""
Vistas de favoritos / social para el OYENTE.

- POST endpoints de toggle (devuelven JSON con el nuevo estado).
- Vistas de lista: "Canciones que me gustan", "Mis Artistas", "Mis Álbumes".
"""

import logging
import traceback

from django.views import View
from django.shortcuts import render
from django.http import JsonResponse, HttpResponseBadRequest
from django.db import DatabaseError

from usuarios.mixins import RequiereOyente
from catalogo.services import (
    deezer_get_artist_image,
    deezer_get_track_image,
    deezer_get_album_image,
    deezer_enrich_canciones,
    deezer_enrich_albumes,
)

from . import services

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
            active = services.toggle_like_cancion(usuario_id, int(pk))
            logger.info('LIKE cancion=%s usuario=%s → %s', pk, usuario_id, active)
            return _ajax_ok(active, kind='like_cancion', target_id=int(pk))
        except DatabaseError as e:
            logger.error('Error toggle_like_cancion: %s', e)
            logger.error(traceback.format_exc())
            return _ajax_err(str(e))

    def get(self, request, pk):
        return HttpResponseBadRequest('Use POST')


class ToggleSeguirArtistaView(RequiereOyente, View):
    def post(self, request, pk):
        usuario_id = _uid(request)
        try:
            active = services.toggle_seguir_artista(usuario_id, int(pk))
            logger.info('FOLLOW artista=%s usuario=%s → %s', pk, usuario_id, active)
            return _ajax_ok(active, kind='seguir_artista', target_id=int(pk))
        except DatabaseError as e:
            logger.error('Error toggle_seguir_artista: %s', e)
            logger.error(traceback.format_exc())
            return _ajax_err(str(e))

    def get(self, request, pk):
        return HttpResponseBadRequest('Use POST')


class ToggleGuardarAlbumView(RequiereOyente, View):
    def post(self, request, pk):
        usuario_id = _uid(request)
        try:
            active = services.toggle_guardar_album(usuario_id, int(pk))
            logger.info('SAVE album=%s usuario=%s → %s', pk, usuario_id, active)
            return _ajax_ok(active, kind='guardar_album', target_id=int(pk))
        except DatabaseError as e:
            logger.error('Error toggle_guardar_album: %s', e)
            logger.error(traceback.format_exc())
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
            canciones = services.get_canciones_liked(usuario_id)
        except DatabaseError as e:
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
            artistas = services.get_artistas_seguidos(usuario_id)
        except DatabaseError as e:
            logger.error('Error cargando artistas seguidos: %s', e)
            artistas = []

        for a in artistas:
            a['foto'] = deezer_get_artist_image(a.get('nombreArtistico') or '')

        return render(request, self.template_name, {
            'artistas': artistas,
            'total': len(artistas),
        })


class MisAlbumesGuardadosView(RequiereOyente, View):
    template_name = 'biblioteca/mis_albumes.html'

    def get(self, request):
        usuario_id = _uid(request)
        try:
            albumes = services.get_albumes_guardados(usuario_id)
        except DatabaseError as e:
            logger.error('Error cargando albumes guardados: %s', e)
            albumes = []

        deezer_enrich_albumes(albumes)
        # (deezer_enrich_albumes pone .coverUrl)

        return render(request, self.template_name, {
            'albumes': albumes,
            'total': len(albumes),
        })

class MisPlaylistsView(RequiereOyente, View):
    template_name = 'biblioteca/playlist_list.html'

    def get(self, request):
        usuario_id = _uid(request)
        try:
            from .services_reportes import sp_listar_playlists
            playlists = sp_listar_playlists(usuario_id)
        except DatabaseError as e:
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
            from .services_reportes import sp_crear_playlist
            sp_crear_playlist(usuario_id, nombre, descripcion, visibilidad, tipo)
        except DatabaseError as e:
            logger.error('Error creando playlist: %s', e)
            return render(request, self.template_name, {
                'error': f'Error: {str(e)}'
            })

        from django.shortcuts import redirect
        return redirect('biblioteca:mis_playlists')
    
class DetallePlaylistView(RequiereOyente, View):
    template_name = 'biblioteca/playlist_detail.html'

    def get(self, request, pk):
        usuario_id = _uid(request)
        try:
            from .services_reportes import get_playlist_info, get_canciones_playlist
            playlist = get_playlist_info(pk, usuario_id)
            if not playlist:
                from django.shortcuts import redirect
                return redirect('biblioteca:mis_playlists')
            canciones = get_canciones_playlist(pk)
        except DatabaseError as e:
            logger.error('Error cargando playlist: %s', e)
            playlist = None
            canciones = []

        # Obtener todas las canciones del catálogo para el select
        try:
            from django.db import connection
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT c.idCancion, c.nombreCancion, ar.nombreArtistico
                    FROM Catalogo.Cancion c
                    INNER JOIN Catalogo.Album a ON a.idAlbum = c.Album_idAlbum
                    INNER JOIN Usuario.Artista ar ON ar.idUsuario = a.Artista_idUsuario
                    WHERE c.estadoCancion = 'activa'
                    ORDER BY ar.nombreArtistico, c.nombreCancion
                    """
                )
                cols = [col[0] for col in cur.description]
                todas_canciones = [dict(zip(cols, row)) for row in cur.fetchall()]
        except DatabaseError:
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
            from .services_reportes import get_playlist_info
            playlist = get_playlist_info(pk, usuario_id)
            if not playlist:
                from django.shortcuts import redirect
                return redirect('biblioteca:mis_playlists')
        except DatabaseError as e:
            logger.error('Error cargando playlist: %s', e)
            from django.shortcuts import redirect
            return redirect('biblioteca:mis_playlists')
        return render(request, self.template_name, {'playlist': playlist})

    def post(self, request, pk):
        usuario_id = _uid(request)
        nombre = request.POST.get('nombre', '').strip()
        descripcion = request.POST.get('descripcion', '').strip()
        visibilidad = request.POST.get('visibilidad', 'Privada')

        if not nombre:
            from .services_reportes import get_playlist_info
            playlist = get_playlist_info(pk, usuario_id)
            return render(request, self.template_name, {
                'playlist': playlist,
                'error': 'El nombre es obligatorio.'
            })

        try:
            from django.db import connection
            with connection.cursor() as cur:
                cur.execute(
                    """
                    UPDATE Biblioteca.Playlist
                    SET nombrePlaylist = %s,
                        descripcionPlaylist = %s,
                        tipoVisibilidad = %s
                    WHERE idPlaylist = %s
                    AND idPlaylist IN (
                        SELECT Playlist_idPlaylist FROM Biblioteca.UsuarioPlaylist
                        WHERE Usuario_idUsuario = %s AND rolPlaylist = 'Creador'
                    )
                    """,
                    [nombre, descripcion, visibilidad, pk, usuario_id]
                )
        except DatabaseError as e:
            logger.error('Error editando playlist: %s', e)
            from .services_reportes import get_playlist_info
            playlist = get_playlist_info(pk, usuario_id)
            return render(request, self.template_name, {
                'playlist': playlist,
                'error': f'No se pudo actualizar: {str(e)}'
            })

        from django.shortcuts import redirect
        return redirect('biblioteca:detalle_playlist', pk=pk)


class EliminarPlaylistView(RequiereOyente, View):

    def post(self, request, pk):
        usuario_id = _uid(request)
        try:
            from django.db import connection
            with connection.cursor() as cur:
                # Verificar que es creador
                cur.execute(
                    """
                    SELECT COUNT(*) FROM Biblioteca.UsuarioPlaylist
                    WHERE Playlist_idPlaylist = %s
                    AND Usuario_idUsuario = %s AND rolPlaylist = 'Creador'
                    """,
                    [pk, usuario_id]
                )
                if cur.fetchone()[0] == 0:
                    from django.shortcuts import redirect
                    return redirect('biblioteca:mis_playlists')

                # Eliminar canciones de la playlist
                cur.execute(
                    "DELETE FROM Biblioteca.CancionPlaylist WHERE Playlist_idPlaylist = %s",
                    [pk]
                )
                # Eliminar usuarios de la playlist
                cur.execute(
                    "DELETE FROM Biblioteca.UsuarioPlaylist WHERE Playlist_idPlaylist = %s",
                    [pk]
                )
                # Eliminar la playlist
                cur.execute(
                    "DELETE FROM Biblioteca.Playlist WHERE idPlaylist = %s",
                    [pk]
                )
        except DatabaseError as e:
            logger.error('Error eliminando playlist: %s', e)

        from django.shortcuts import redirect
        return redirect('biblioteca:mis_playlists')
    
class AgregarCancionPlaylistView(RequiereOyente, View):

    def post(self, request, pk):
        usuario_id = _uid(request)
        cancion_id = request.POST.get('cancion_id')
        from django.shortcuts import redirect

        if not cancion_id:
            return redirect('biblioteca:detalle_playlist', pk=pk)

        try:
            from django.db import connection
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM Biblioteca.UsuarioPlaylist
                    WHERE Playlist_idPlaylist = %s
                    AND Usuario_idUsuario = %s
                    AND rolPlaylist = 'Creador'
                    """,
                    [pk, usuario_id]
                )
                if cur.fetchone()[0] == 0:
                    return redirect('biblioteca:detalle_playlist', pk=pk)

                cur.execute(
                    "SELECT ISNULL(MAX(posicionPlaylist), 0) + 1 FROM Biblioteca.CancionPlaylist WHERE Playlist_idPlaylist = %s",
                    [pk]
                )
                posicion = cur.fetchone()[0]

                cur.execute(
                    """
                    SELECT COUNT(*) FROM Biblioteca.CancionPlaylist
                    WHERE Playlist_idPlaylist = %s AND Cancion_idCancion = %s
                    """,
                    [pk, cancion_id]
                )
                if cur.fetchone()[0] > 0:
                    return redirect('biblioteca:detalle_playlist', pk=pk)

                cur.execute(
                    """
                    INSERT INTO Biblioteca.CancionPlaylist
                    (Playlist_idPlaylist, Cancion_idCancion, posicionPlaylist, fechaAgregada)
                    VALUES (%s, %s, %s, GETDATE())
                    """,
                    [pk, cancion_id, posicion]
                )
        except DatabaseError as e:
            logger.error('Error agregando cancion a playlist: %s', e)

        return redirect('biblioteca:detalle_playlist', pk=pk)


class EliminarCancionPlaylistView(RequiereOyente, View):

    def post(self, request, pk, cancion_pk):
        usuario_id = _uid(request)

        try:
            from django.db import connection
            with connection.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM Biblioteca.CancionPlaylist
                    WHERE Playlist_idPlaylist = %s
                    AND Cancion_idCancion = %s
                    AND Playlist_idPlaylist IN (
                        SELECT Playlist_idPlaylist FROM Biblioteca.UsuarioPlaylist
                        WHERE Usuario_idUsuario = %s AND rolPlaylist = 'Creador'
                    )
                    """,
                    [pk, cancion_pk, usuario_id]
                )
        except DatabaseError as e:
            logger.error('Error eliminando cancion de playlist: %s', e)

        from django.shortcuts import redirect
        return redirect('biblioteca:detalle_playlist', pk=pk)