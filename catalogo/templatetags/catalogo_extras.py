"""Filtros y tags personalizados para los templates del catálogo."""

from django import template

register = template.Library()


@register.filter(name='split')
def split_filter(value, separator=','):
    """Divide un string por el separador dado y devuelve la lista resultante.

    Uso en template:
        {% for g in cancion.generosCSV|split:"," %}{{ g|strip }}{% endfor %}
    """
    if not value:
        return []
    return [item.strip() for item in str(value).split(separator) if item.strip()]


@register.filter(name='strip')
def strip_filter(value):
    """Elimina espacios al inicio y final del valor."""
    if value is None:
        return ''
    return str(value).strip()
