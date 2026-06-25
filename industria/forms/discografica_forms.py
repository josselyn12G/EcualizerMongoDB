"""Form (sin ORM) para Discográfica sobre MongoDB."""

import re
from django import forms

from ..mongo_service import nombre_disco_existe

_INPUT = {'class': 'form-control'}


class DiscograficaForm(forms.Form):
    nombre_discografica = forms.CharField(
        label='Nombre', max_length=150,
        widget=forms.TextInput(attrs={**_INPUT, 'placeholder': 'Nombre legal'}))
    pais_origen = forms.CharField(
        label='País de origen', max_length=80,
        widget=forms.TextInput(attrs={**_INPUT, 'placeholder': 'Ecuador'}))
    correo_contacto = forms.CharField(
        label='Correo de contacto',
        widget=forms.EmailInput(attrs={**_INPUT, 'placeholder': 'contacto@disco.com'}))
    telefono_contacto = forms.CharField(
        label='Teléfono de contacto',
        widget=forms.TextInput(attrs={**_INPUT, 'placeholder': '0999999999', 'maxlength': 10}))

    def __init__(self, *args, exclude_pk=None, **kwargs):
        self.exclude_pk = exclude_pk
        super().__init__(*args, **kwargs)

    def clean_telefono_contacto(self):
        tel = (self.cleaned_data.get('telefono_contacto') or '').strip()
        if not re.fullmatch(r'\d{10}', tel):
            raise forms.ValidationError('El teléfono debe tener exactamente 10 dígitos numéricos.')
        return tel

    def clean_correo_contacto(self):
        correo = (self.cleaned_data.get('correo_contacto') or '').strip().lower()
        if not re.fullmatch(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', correo):
            raise forms.ValidationError('Formato de correo inválido.')
        return correo

    def clean_nombre_discografica(self):
        nombre = (self.cleaned_data.get('nombre_discografica') or '').strip()
        if nombre_disco_existe(nombre, exclude_pk=self.exclude_pk):
            raise forms.ValidationError('Ya existe una discográfica con ese nombre.')
        return nombre
