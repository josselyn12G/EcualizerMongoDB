"""Formularios del módulo de pagos (panel admin)."""
from django import forms

DURACION_CHOICES = [('Mensual', 'Mensual'), ('Anual', 'Anual')]


class PlanForm(forms.Form):
    """Crear / editar un plan del catálogo (colección Plan en MongoDB)."""
    nombre_plan = forms.CharField(
        label='Nombre del plan', max_length=60,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Premium Individual'}))
    precio = forms.DecimalField(
        label='Precio (USD)', min_value=0, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}))
    duracion = forms.ChoiceField(
        label='Duración', choices=DURACION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}))
    descripcion = forms.CharField(
        label='Descripción', required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3,
                                     'placeholder': 'Características del plan (opcional)'}))

    def clean_nombre_plan(self):
        nombre = self.cleaned_data.get('nombre_plan', '').strip()
        if len(nombre) < 2:
            raise forms.ValidationError('El nombre debe tener al menos 2 caracteres.')
        return nombre
