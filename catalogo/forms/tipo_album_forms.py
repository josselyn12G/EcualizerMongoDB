"""Forms para TipoAlbum (admin)."""

from django import forms
from django.core.exceptions import ValidationError


class TipoAlbumForm(forms.Form):
    nombre_tipo = forms.CharField(
        label='Nombre del tipo',
        max_length=20,
        min_length=2,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej. LP, EP, Single, Compilation…',
        }),
    )
    descripcion_tipo = forms.CharField(
        label='Descripción',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Descripción opcional del tipo de álbum',
        }),
    )

    def clean_nombre_tipo(self):
        v = (self.cleaned_data.get('nombre_tipo') or '').strip()
        if len(v) < 2:
            raise ValidationError('Debe tener al menos 2 caracteres.')
        return v
