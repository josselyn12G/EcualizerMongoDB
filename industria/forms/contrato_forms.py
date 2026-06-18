"""Forms CRUD de ContratoDiscografica."""

from django import forms
from ..models import ContratoDiscografica
from usuarios.models import Artista
from .discografica_forms import Discografica


class ContratoForm(forms.ModelForm):
    artista = forms.ModelChoiceField(
        label='Artista',
        queryset=Artista.objects.all().order_by('nombre_artistico'),
        empty_label='-- Selecciona un artista --',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    discografica = forms.ModelChoiceField(
        label='Discográfica',
        queryset=Discografica.objects.all().order_by('nombre_discografica'),
        empty_label='-- Selecciona una discográfica --',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = ContratoDiscografica
        fields = [
            'artista', 'discografica',
            'fecha_inicio', 'fecha_fin',
            'porcentaje_artista', 'porcentaje_discografica',
            'estado_contrato',
        ]
        widgets = {
            'fecha_inicio':            forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin':               forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'porcentaje_artista':      forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0, 'max': 100}),
            'porcentaje_discografica': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': 0, 'max': 100}),
            'estado_contrato':         forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned = super().clean()
        ini = cleaned.get('fecha_inicio')
        fin = cleaned.get('fecha_fin')
        if ini and fin and fin <= ini:
            self.add_error('fecha_fin', 'La fecha de fin debe ser mayor a la de inicio.')

        a = cleaned.get('porcentaje_artista') or 0
        d = cleaned.get('porcentaje_discografica') or 0
        if (a + d) > 100:
            self.add_error('porcentaje_discografica',
                           'La suma de porcentajes no puede superar 100%.')
        return cleaned
