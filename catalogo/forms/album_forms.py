"""
Forms de Album.

Validaciones equivalentes a los CHECKs de SQL:
  - tituloAlbum: longitud 2-40
  - estadoAlbum IN ('activo', 'inactivo', 'eliminado')
  - fechaLanzamientoAlbum: requerido (default GETDATE())
"""

from django import forms
from django.core.exceptions import ValidationError

from ..models import Album, TipoAlbum


# ──────────────────────────────────────────────────────────
# BASE
# ──────────────────────────────────────────────────────────
class _AlbumBaseForm(forms.ModelForm):
    """Mixin con los widgets/estilos Bootstrap comunes."""

    titulo_album = forms.CharField(
        label='Título del álbum',
        max_length=40,
        min_length=2,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej. Midnight Echoes',
        }),
    )
    fecha_lanzamiento_album = forms.DateField(
        label='Fecha de lanzamiento',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    descripcion_album = forms.CharField(
        label='Descripción',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Descripción opcional del álbum',
        }),
    )
    tipo_album = forms.ModelChoiceField(
        label='Tipo de álbum',
        queryset=TipoAlbum.objects.all(),
        empty_label='-- Selecciona un tipo --',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    def clean_titulo_album(self):
        titulo = (self.cleaned_data.get('titulo_album') or '').strip()
        if len(titulo) < 2:
            raise ValidationError('El título debe tener al menos 2 caracteres.')
        return titulo


# ──────────────────────────────────────────────────────────
# ARTISTA — Crear
# ──────────────────────────────────────────────────────────
class AlbumCreateForm(_AlbumBaseForm):
    """Form que usa el artista para crear un álbum nuevo.

    El estado se fija en 'activo' por defecto, el artista no lo elige.
    El campo Artista se inyecta desde la vista (request.session['usuario_id']).
    """

    class Meta:
        model = Album
        fields = [
            'titulo_album',
            'fecha_lanzamiento_album',
            'descripcion_album',
            'tipo_album',
        ]


# ──────────────────────────────────────────────────────────
# ARTISTA — Editar
# ──────────────────────────────────────────────────────────
class AlbumUpdateForm(_AlbumBaseForm):
    """El artista solo puede modificar sus propios álbumes.
    No cambia estado (eso es responsabilidad del admin).
    """

    class Meta:
        model = Album
        fields = [
            'titulo_album',
            'fecha_lanzamiento_album',
            'descripcion_album',
            'tipo_album',
        ]


# ──────────────────────────────────────────────────────────
# ADMIN — Editar (incluye cambio de estado)
# ──────────────────────────────────────────────────────────
class AlbumAdminUpdateForm(_AlbumBaseForm):
    """El admin puede modificar todos los campos, incluido el estado."""

    estado_album = forms.ChoiceField(
        label='Estado',
        choices=Album.ESTADO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = Album
        fields = [
            'titulo_album',
            'fecha_lanzamiento_album',
            'descripcion_album',
            'tipo_album',
            'estado_album',
        ]


# ──────────────────────────────────────────────────────────
# ADMIN — Reportar (no edita Album, manda comentario)
# ──────────────────────────────────────────────────────────
class AlbumReportForm(forms.Form):
    """Reporte de un álbum: el admin envía un comentario al artista."""

    motivo = forms.CharField(
        label='Motivo del reporte',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej. Contenido inapropiado',
        }),
    )
    comentario = forms.CharField(
        label='Comentario / observación',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Detalla la razón del reporte para que el artista corrija…',
        }),
    )
