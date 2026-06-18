"""URLs de la app `biblioteca` (favoritos / social)."""

from django.urls import path

from .views import (
    ToggleLikeCancionView,
    ToggleSeguirArtistaView,
    ToggleGuardarAlbumView,
    MisCancionesLikedView,
    MisArtistasSeguidosView,
    MisAlbumesGuardadosView,
    MisPlaylistsView,
    CrearPlaylistView,
    DetallePlaylistView,
    EditarPlaylistView,
    EliminarPlaylistView,
    AgregarCancionPlaylistView,
    EliminarCancionPlaylistView,
)


app_name = 'biblioteca'

urlpatterns = [
    # ── Toggles (POST → JSON) ──────────────────────────
    path('like/cancion/<int:pk>/',
         ToggleLikeCancionView.as_view(),
         name='toggle_like_cancion'),
    path('seguir/artista/<int:pk>/',
         ToggleSeguirArtistaView.as_view(),
         name='toggle_seguir_artista'),
    path('guardar/album/<int:pk>/',
         ToggleGuardarAlbumView.as_view(),
         name='toggle_guardar_album'),

    # ── Listas ───────────────────────────────────────
    path('mis-canciones/',
         MisCancionesLikedView.as_view(),
         name='mis_canciones_liked'),
    path('mis-artistas/',
         MisArtistasSeguidosView.as_view(),
         name='mis_artistas'),
    path('mis-albumes/',
         MisAlbumesGuardadosView.as_view(),
         name='mis_albumes'),
    
    # Playlists
    path('mis-playlists/',
         MisPlaylistsView.as_view(),
         name='mis_playlists'),
    path('mis-playlists/crear/',
         CrearPlaylistView.as_view(),
         name='crear_playlist'),
    path('mis-playlists/<int:pk>/',
         DetallePlaylistView.as_view(),
         name='detalle_playlist'),
    path('mis-playlists/<int:pk>/editar/',
         EditarPlaylistView.as_view(),
         name='editar_playlist'),
    path('mis-playlists/<int:pk>/eliminar/',
         EliminarPlaylistView.as_view(),
         name='eliminar_playlist'),
    path('mis-playlists/<int:pk>/agregar-cancion/',
         AgregarCancionPlaylistView.as_view(),
         name='agregar_cancion_playlist'),
    path('mis-playlists/<int:pk>/eliminar-cancion/<int:cancion_pk>/',
         EliminarCancionPlaylistView.as_view(),
         name='eliminar_cancion_playlist'),
]
