"""Forms para GeneroMusical (admin)."""

from django import forms
from django.core.exceptions import ValidationError


class GeneroForm(forms.Form):
    """Form simple para crear/editar género (no usa ModelForm porque el SP
    valida unicidad y maneja la generación de id manualmente)."""

    nombre_genero = forms.CharField(
        label='Nombre del género',
        max_length=40,
        min_length=2,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej. Reggaetón, Indie, Salsa…',
        }),
    )

    def clean_nombre_genero(self):
        v = (self.cleaned_data.get('nombre_genero') or '').strip()
        if len(v) < 2:
            raise ValidationError('Debe tener al menos 2 caracteres.')
        return v
