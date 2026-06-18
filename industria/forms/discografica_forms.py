"""Forms CRUD de Discográfica."""

import re
from django import forms
from ..models import Discografica


class DiscograficaForm(forms.ModelForm):
    class Meta:
        model = Discografica
        fields = ['nombre_discografica', 'pais_origen',
                  'correo_contacto', 'telefono_contacto']
        widgets = {
            'nombre_discografica': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre legal'}),
            'pais_origen':         forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ecuador'}),
            'correo_contacto':     forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'contacto@disco.com'}),
            'telefono_contacto':   forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0999999999', 'maxlength': 10}),
        }

    def clean_telefono_contacto(self):
        tel = self.cleaned_data.get('telefono_contacto', '').strip()
        if not re.fullmatch(r'\d{10}', tel):
            raise forms.ValidationError('El teléfono debe tener exactamente 10 dígitos numéricos.')
        return tel

    def clean_correo_contacto(self):
        correo = self.cleaned_data.get('correo_contacto', '').strip().lower()
        if '@' not in correo or '.' not in correo.split('@')[-1]:
            raise forms.ValidationError('Formato de correo inválido.')
        return correo

    def clean_nombre_discografica(self):
        nombre = self.cleaned_data.get('nombre_discografica', '').strip()
        qs = Discografica.objects.filter(nombre_discografica__iexact=nombre)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Ya existe una discográfica con ese nombre.')
        return nombre
