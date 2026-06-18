"""
Forms de Cancion.

Validaciones equivalentes a los CHECKs de SQL:
  - duracion > 0
  - calidadKbps IN (128, 192, 256, 320)
  - estadoCancion IN ('activa', 'inactiva', 'bloqueada', 'eliminada')
  - numeroPista > 0
  - totalReproducciones >= 0 (no editable directamente)
"""

from django import forms
from django.core.exceptions import ValidationError

from ..models import Cancion, Album, GeneroMusical


# ──────────────────────────────────────────────────────────
# BASE
# ──────────────────────────────────────────────────────────
class _CancionBaseForm(forms.ModelForm):
    nombre_cancion = forms.CharField(
        label='Nombre',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej. Tide',
        }),
    )
    duracion = forms.IntegerField(
        label='Duración (segundos)',
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '180',
        }),
    )
    fecha_lanzamiento = forms.DateField(
        label='Fecha de lanzamiento',
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    calidad_kbps = forms.TypedChoiceField(
        label='Calidad (kbps)',
        choices=Cancion.CALIDAD_CHOICES,
        coerce=int,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    numero_pista = forms.IntegerField(
        label='Número de pista',
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '1'}),
    )
    letra_cancion = forms.CharField(
        label='Letra',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Letra de la canción (opcional)',
        }),
    )
    generos = forms.ModelMultipleChoiceField(
        label='Géneros musicales',
        queryset=GeneroMusical.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'size': 6,
        }),
    )

    # ── validaciones específicas ─────────────────────────
    def clean_duracion(self):
        d = self.cleaned_data.get('duracion')
        if d is None or d <= 0:
            raise ValidationError('La duración debe ser mayor que 0 segundos.')
        return d

    def clean_calidad_kbps(self):
        k = self.cleaned_data.get('calidad_kbps')
        if k not in (128, 192, 256, 320):
            raise ValidationError('La calidad debe ser 128, 192, 256 o 320 kbps.')
        return k

    def clean_numero_pista(self):
        n = self.cleaned_data.get('numero_pista')
        if n is None or n <= 0:
            raise ValidationError('El número de pista debe ser mayor que 0.')
        return n


# ──────────────────────────────────────────────────────────
# ARTISTA — Crear
# ──────────────────────────────────────────────────────────
class CancionCreateForm(_CancionBaseForm):
    """El artista crea una canción dentro de uno de sus álbumes."""

    album = forms.ModelChoiceField(
        label='Álbum',
        queryset=Album.objects.none(),
        empty_label='-- Selecciona un álbum --',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = Cancion
        fields = [
            'nombre_cancion',
            'album',
            'numero_pista',
            'duracion',
            'fecha_lanzamiento',
            'calidad_kbps',
            'letra_cancion',
            'generos',
        ]

    def __init__(self, *args, artista_id=None, **kwargs):
        """artista_id se inyecta desde la vista para filtrar sus álbumes."""
        super().__init__(*args, **kwargs)
        if artista_id is not None:
            self.fields['album'].queryset = Album.objects.filter(
                artista_id=artista_id,
                estado_album='activo',
            )


# ──────────────────────────────────────────────────────────
# ARTISTA — Editar
# ──────────────────────────────────────────────────────────
class CancionUpdateForm(_CancionBaseForm):
    """Edita los campos editables — no cambia estado ni reproducciones."""

    album = forms.ModelChoiceField(
        label='Álbum',
        queryset=Album.objects.none(),
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = Cancion
        fields = [
            'nombre_cancion',
            'album',
            'numero_pista',
            'duracion',
            'fecha_lanzamiento',
            'calidad_kbps',
            'letra_cancion',
            'generos',
        ]

    def __init__(self, *args, artista_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        if artista_id is not None:
            self.fields['album'].queryset = Album.objects.filter(
                artista_id=artista_id,
                estado_album='activo',
            )


# ──────────────────────────────────────────────────────────
# ADMIN — Editar (incluye estado). Los géneros NO se editan aquí:
# se gestionan con chips/agregar/quitar individualmente (M:N).
# ──────────────────────────────────────────────────────────
class CancionAdminUpdateForm(_CancionBaseForm):
    estado_cancion = forms.ChoiceField(
        label='Estado',
        choices=Cancion.ESTADO_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    # Removemos el ModelMultipleChoiceField heredado del base
    generos = None

    class Meta:
        model = Cancion
        fields = [
            'nombre_cancion',
            'numero_pista',
            'duracion',
            'fecha_lanzamiento',
            'calidad_kbps',
            'letra_cancion',
            'estado_cancion',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Eliminar el field 'generos' que viene del base
        if 'generos' in self.fields:
            del self.fields['generos']


# ──────────────────────────────────────────────────────────
# ADMIN — Reportar
# ──────────────────────────────────────────────────────────
class CancionReportForm(forms.Form):
    motivo = forms.CharField(
        label='Motivo del reporte',
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej. Copyright',
        }),
    )
    comentario = forms.CharField(
        label='Comentario al artista',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Detalla la razón del reporte…',
        }),
    )
