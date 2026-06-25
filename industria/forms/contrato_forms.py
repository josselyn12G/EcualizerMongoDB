"""Form (sin ORM) para ContratoDiscografica sobre MongoDB."""

from django import forms

from ..mongo_service import (
    artistas_choices, discograficas_choices, ESTADOS_CONTRATO,
)

_INPUT = {'class': 'form-control'}
_SELECT = {'class': 'form-select'}


class ContratoForm(forms.Form):
    artista = forms.ChoiceField(
        label='Artista', choices=[], widget=forms.Select(attrs=_SELECT))
    discografica = forms.ChoiceField(
        label='Discográfica', choices=[], widget=forms.Select(attrs=_SELECT))
    fecha_inicio = forms.DateField(
        label='Fecha de inicio',
        widget=forms.DateInput(attrs={**_INPUT, 'type': 'date'}))
    fecha_fin = forms.DateField(
        label='Fecha de fin', required=False,
        widget=forms.DateInput(attrs={**_INPUT, 'type': 'date'}))
    porcentaje_artista = forms.DecimalField(
        label='% Artista', min_value=0, max_value=100, decimal_places=2,
        widget=forms.NumberInput(attrs={**_INPUT, 'step': '0.01', 'min': 0, 'max': 100}))
    porcentaje_discografica = forms.DecimalField(
        label='% Discográfica', min_value=0, max_value=100, decimal_places=2,
        widget=forms.NumberInput(attrs={**_INPUT, 'step': '0.01', 'min': 0, 'max': 100}))
    estado_contrato = forms.ChoiceField(
        label='Estado', choices=[(e, e) for e in ESTADOS_CONTRATO],
        widget=forms.Select(attrs=_SELECT))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['artista'].choices = (
            [('', '-- Selecciona un artista --')] + artistas_choices())
        self.fields['discografica'].choices = (
            [('', '-- Selecciona una discográfica --')] + discograficas_choices())

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
