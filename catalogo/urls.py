"""
URLs de la app `catalogo`.

Estructura:
  catalogo/
    ├── artista/album/...
    ├── artista/cancion/...
    ├── usuario/album/...
    ├── usuario/cancion/...
    ├── admin/album/...
    └── admin/cancion/...
"""

from django.urls import path

from .views.artista.album_views import (
    ArtistaAlbumListView, ArtistaAlbumCreateView,
    ArtistaAlbumUpdateView, ArtistaAlbumDeactivateView,
    ArtistaAlbumDeleteView, ArtistaAlbumDetailView,
)
from .views.artista.cancion_views import (
    ArtistaCancionListView, ArtistaCancionCreateView,
    ArtistaCancionUpdateView, ArtistaCancionDeactivateView,
)
from .views.usuario.album_views import (
    UsuarioAlbumListView, UsuarioAlbumDetailView, UsuarioAlbumSearchView,
)
from .views.usuario.cancion_views import (
    UsuarioCancionListView, UsuarioCancionDetailView, UsuarioCancionFilterView,
    UsuarioCancionPreviewView,
)
from .views.usuario.artista_views import (
    UsuarioArtistaListView, UsuarioArtistaDetailView,
)
from .views.administrador.album_views import (
    AdminAlbumListView, AdminAlbumUpdateView,
    AdminAlbumDetailView, AdminAlbumReportView,
)
from .views.administrador.cancion_views import (
    AdminCancionListView, AdminCancionUpdateView,
    AdminCancionDetailView, AdminCancionDeactivateView,
    AdminCancionReportView,
    AdminCancionGeneroAddView, AdminCancionGeneroRemoveView,
)
from .views.administrador.genero_views import (
    AdminGeneroListView, AdminGeneroCreateView, AdminGeneroUpdateView,
    AdminGeneroDetailView, AdminGeneroDeleteView,
)
from .views.administrador.tipo_album_views import (
    AdminTipoAlbumListView, AdminTipoAlbumCreateView, AdminTipoAlbumUpdateView,
    AdminTipoAlbumDetailView, AdminTipoAlbumDeleteView,
)


app_name = 'catalogo'

urlpatterns = [
    # ═════════════════════════════════════════════════════
    # ARTISTA · Album
    # ═════════════════════════════════════════════════════
    path('artista/albumes/',
         ArtistaAlbumListView.as_view(),
         name='artista_album_list'),
    path('artista/albumes/nuevo/',
         ArtistaAlbumCreateView.as_view(),
         name='artista_album_create'),
    path('artista/albumes/<int:pk>/',
         ArtistaAlbumDetailView.as_view(),
         name='artista_album_detail'),
    path('artista/albumes/<int:pk>/editar/',
         ArtistaAlbumUpdateView.as_view(),
         name='artista_album_update'),
    path('artista/albumes/<int:pk>/desactivar/',
         ArtistaAlbumDeactivateView.as_view(),
         name='artista_album_deactivate'),
    path('artista/albumes/<int:pk>/eliminar/',
         ArtistaAlbumDeleteView.as_view(),
         name='artista_album_delete'),

    # ═════════════════════════════════════════════════════
    # ARTISTA · Cancion
    # ═════════════════════════════════════════════════════
    path('artista/canciones/',
         ArtistaCancionListView.as_view(),
         name='artista_cancion_list'),
    path('artista/canciones/nueva/',
         ArtistaCancionCreateView.as_view(),
         name='artista_cancion_create'),
    path('artista/canciones/<int:pk>/editar/',
         ArtistaCancionUpdateView.as_view(),
         name='artista_cancion_update'),
    path('artista/canciones/<int:pk>/desactivar/',
         ArtistaCancionDeactivateView.as_view(),
         name='artista_cancion_deactivate'),

    # ═════════════════════════════════════════════════════
    # USUARIO (oyente) · Album
    # ═════════════════════════════════════════════════════
    path('albumes/',
         UsuarioAlbumListView.as_view(),
         name='usuario_album_list'),
    path('albumes/buscar/',
         UsuarioAlbumSearchView.as_view(),
         name='usuario_album_search'),
    path('albumes/<int:pk>/',
         UsuarioAlbumDetailView.as_view(),
         name='usuario_album_detail'),

    # ═════════════════════════════════════════════════════
    # USUARIO (oyente) · Cancion
    # ═════════════════════════════════════════════════════
    path('canciones/',
         UsuarioCancionListView.as_view(),
         name='usuario_cancion_list'),
    path('canciones/<int:pk>/',
         UsuarioCancionDetailView.as_view(),
         name='usuario_cancion_detail'),
    path('canciones/genero/<int:genero_id>/',
         UsuarioCancionFilterView.as_view(),
         name='usuario_cancion_filter'),
    path('canciones/<int:pk>/preview/',
         UsuarioCancionPreviewView.as_view(),
         name='usuario_cancion_preview'),

    # ═════════════════════════════════════════════════════
    # USUARIO (oyente) · Artistas
    # ═════════════════════════════════════════════════════
    path('artistas/',
         UsuarioArtistaListView.as_view(),
         name='usuario_artista_list'),
    path('artistas/<int:pk>/',
         UsuarioArtistaDetailView.as_view(),
         name='usuario_artista_detail'),

    # ═════════════════════════════════════════════════════
    # ADMIN · Album
    # ═════════════════════════════════════════════════════
    path('admin/albumes/',
         AdminAlbumListView.as_view(),
         name='admin_album_list'),
    path('admin/albumes/<int:pk>/',
         AdminAlbumDetailView.as_view(),
         name='admin_album_detail'),
    path('admin/albumes/<int:pk>/editar/',
         AdminAlbumUpdateView.as_view(),
         name='admin_album_update'),
    path('admin/albumes/<int:pk>/reportar/',
         AdminAlbumReportView.as_view(),
         name='admin_album_report'),

    # ═════════════════════════════════════════════════════
    # ADMIN · Cancion
    # ═════════════════════════════════════════════════════
    path('admin/canciones/',
         AdminCancionListView.as_view(),
         name='admin_cancion_list'),
    path('admin/canciones/<int:pk>/',
         AdminCancionDetailView.as_view(),
         name='admin_cancion_detail'),
    path('admin/canciones/<int:pk>/editar/',
         AdminCancionUpdateView.as_view(),
         name='admin_cancion_update'),
    path('admin/canciones/<int:pk>/desactivar/',
         AdminCancionDeactivateView.as_view(),
         name='admin_cancion_deactivate'),
    path('admin/canciones/<int:pk>/reportar/',
         AdminCancionReportView.as_view(),
         name='admin_cancion_report'),
    # M:N géneros
    path('admin/canciones/<int:pk>/genero/agregar/',
         AdminCancionGeneroAddView.as_view(),
         name='admin_cancion_genero_add'),
    path('admin/canciones/<int:pk>/genero/<int:genero_id>/quitar/',
         AdminCancionGeneroRemoveView.as_view(),
         name='admin_cancion_genero_remove'),

    # ═════════════════════════════════════════════════════
    # ADMIN · GeneroMusical · CRUD
    # ═════════════════════════════════════════════════════
    path('admin/generos/',
         AdminGeneroListView.as_view(),
         name='admin_genero_list'),
    path('admin/generos/nuevo/',
         AdminGeneroCreateView.as_view(),
         name='admin_genero_create'),
    path('admin/generos/<int:pk>/',
         AdminGeneroDetailView.as_view(),
         name='admin_genero_detail'),
    path('admin/generos/<int:pk>/editar/',
         AdminGeneroUpdateView.as_view(),
         name='admin_genero_update'),
    path('admin/generos/<int:pk>/eliminar/',
         AdminGeneroDeleteView.as_view(),
         name='admin_genero_delete'),

    # ═════════════════════════════════════════════════════
    # ADMIN · TipoAlbum · CRUD
    # ═════════════════════════════════════════════════════
    path('admin/tipos-album/',
         AdminTipoAlbumListView.as_view(),
         name='admin_tipo_album_list'),
    path('admin/tipos-album/nuevo/',
         AdminTipoAlbumCreateView.as_view(),
         name='admin_tipo_album_create'),
    path('admin/tipos-album/<int:pk>/',
         AdminTipoAlbumDetailView.as_view(),
         name='admin_tipo_album_detail'),
    path('admin/tipos-album/<int:pk>/editar/',
         AdminTipoAlbumUpdateView.as_view(),
         name='admin_tipo_album_update'),
    path('admin/tipos-album/<int:pk>/eliminar/',
         AdminTipoAlbumDeleteView.as_view(),
         name='admin_tipo_album_delete'),
]
