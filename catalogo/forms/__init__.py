from .album_forms import AlbumCreateForm, AlbumUpdateForm, AlbumAdminUpdateForm, AlbumReportForm
from .cancion_forms import CancionCreateForm, CancionUpdateForm, CancionAdminUpdateForm, CancionReportForm
from .genero_forms import GeneroForm
from .tipo_album_forms import TipoAlbumForm

__all__ = [
    'AlbumCreateForm', 'AlbumUpdateForm', 'AlbumAdminUpdateForm', 'AlbumReportForm',
    'CancionCreateForm', 'CancionUpdateForm', 'CancionAdminUpdateForm', 'CancionReportForm',
    'GeneroForm', 'TipoAlbumForm',
]
