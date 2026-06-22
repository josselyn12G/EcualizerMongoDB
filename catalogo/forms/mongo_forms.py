"""Formularios (sin ORM) para el catálogo sobre MongoDB."""
from django import forms

TIPO_ALBUM_CHOICES = [('Single', 'Single'), ('EP', 'EP'), ('Album', 'Album')]
ESTADO_ALBUM_CHOICES = [('activo', 'Activo'), ('inactivo', 'Inactivo'), ('eliminado', 'Eliminado')]
ESTADO_CANCION_CHOICES = [('activa', 'Activa'), ('inactiva', 'Inactiva'),
                          ('bloqueada', 'Bloqueada'), ('eliminada', 'Eliminada')]
CALIDAD_CHOICES = [(128, '128 kbps'), (192, '192 kbps'), (256, '256 kbps'), (320, '320 kbps')]

_INPUT = {'class': 'field-input form-control'}
_SELECT = {'class': 'field-select form-select'}
_AREA = {'class': 'field-textarea form-control', 'rows': 3}


class MongoAlbumForm(forms.Form):
    """Crear/editar álbum (artista). El admin añade 'estado' (subclase)."""
    titulo = forms.CharField(label='Título del álbum', max_length=40,
                             widget=forms.TextInput(attrs=_INPUT))
    fecha_lanzamiento = forms.DateField(
        label='Fecha de lanzamiento',
        widget=forms.DateInput(attrs={**_INPUT, 'type': 'date'}))
    tipo = forms.ChoiceField(label='Tipo de álbum', choices=TIPO_ALBUM_CHOICES,
                             widget=forms.Select(attrs=_SELECT))
    descripcion = forms.CharField(label='Descripción', required=False,
                                  widget=forms.Textarea(attrs=_AREA))

    def clean_titulo(self):
        t = self.cleaned_data.get('titulo', '').strip()
        if len(t) < 2:
            raise forms.ValidationError('El título debe tener al menos 2 caracteres.')
        return t


class MongoAlbumAdminForm(MongoAlbumForm):
    estado = forms.ChoiceField(label='Estado', choices=ESTADO_ALBUM_CHOICES,
                               widget=forms.Select(attrs=_SELECT))


class AlbumReporteForm(forms.Form):
    motivo = forms.CharField(label='Motivo del reporte',
                             widget=forms.Textarea(attrs=_AREA))


class MongoCancionForm(forms.Form):
    """Crear/editar canción (artista)."""
    titulo = forms.CharField(label='Título de la canción', max_length=80,
                             widget=forms.TextInput(attrs=_INPUT))
    album_id = forms.ChoiceField(label='Álbum', choices=[],
                                 widget=forms.Select(attrs=_SELECT))
    duracion = forms.IntegerField(label='Duración (segundos)', min_value=1,
                                  widget=forms.NumberInput(attrs=_INPUT))
    numero_pista = forms.IntegerField(label='Número de pista', min_value=1,
                                      widget=forms.NumberInput(attrs=_INPUT))
    calidad = forms.ChoiceField(label='Calidad', choices=CALIDAD_CHOICES,
                                widget=forms.Select(attrs=_SELECT))
    genero = forms.CharField(label='Género principal', required=False,
                             widget=forms.TextInput(attrs=_INPUT))
    letra = forms.CharField(label='Letra (opcional)', required=False,
                            widget=forms.Textarea(attrs=_AREA))

    def __init__(self, *args, album_choices=None, **kwargs):
        super().__init__(*args, **kwargs)
        if album_choices is not None:
            self.fields['album_id'].choices = album_choices


class MongoCancionAdminForm(MongoCancionForm):
    estado = forms.ChoiceField(label='Estado', choices=ESTADO_CANCION_CHOICES,
                               widget=forms.Select(attrs=_SELECT))
