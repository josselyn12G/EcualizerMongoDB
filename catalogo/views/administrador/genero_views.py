"""
CRUD de géneros para el administrador — MongoDB (géneros embebidos en Cancion).
"""

from django import forms
from django.views.generic import View
from django.shortcuts import render, redirect
from django.contrib import messages

from usuarios.mixins import RequiereAdmin
from ...services.catalogo_mongo import (
    listar_generos_mongo,
    crear_genero_mongo,
    renombrar_genero_mongo,
    eliminar_genero_mongo,
)
from ...services.cancion_mongo import agregar_genero_cancion  # noqa (available for future use)


class _GeneroForm(forms.Form):
    nombre_genero = forms.CharField(
        label='Nombre del género', max_length=60,
        widget=forms.TextInput(attrs={'class': 'field-input form-control'}),
    )


class AdminGeneroListView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_genero.html'

    def get(self, request):
        busqueda = request.GET.get('q') or None
        generos = listar_generos_mongo(busqueda=busqueda)
        return render(request, self.template_name, {
            'generos': generos, 'busqueda': busqueda or '', 'modo': 'list',
        })


class AdminGeneroCreateView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_genero.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': _GeneroForm(), 'modo': 'create',
        })

    def post(self, request):
        form = _GeneroForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form, 'modo': 'create'})
        nombre = form.cleaned_data['nombre_genero'].strip()
        if crear_genero_mongo(nombre):
            messages.success(request, f'Género "{nombre}" registrado en el catálogo.')
        else:
            messages.warning(request, f'El género "{nombre}" ya existe.')
        return redirect('catalogo:admin_genero_list')


class AdminGeneroUpdateView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_genero.html'

    def get(self, request, pk):
        # pk = nombre del género (URL-encoded string)
        form = _GeneroForm(initial={'nombre_genero': pk})
        return render(request, self.template_name, {
            'form': form, 'genero': {'nombre': pk}, 'modo': 'update',
        })

    def post(self, request, pk):
        form = _GeneroForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {
                'form': form, 'genero': {'nombre': pk}, 'modo': 'update',
            })
        nuevo = form.cleaned_data['nombre_genero'].strip()
        renombrar_genero_mongo(pk, nuevo)
        messages.success(request, f'Género renombrado de "{pk}" a "{nuevo}".')
        return redirect('catalogo:admin_genero_list')


class AdminGeneroDetailView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_genero.html'

    def get(self, request, pk):
        from types import SimpleNamespace
        from ...services.cancion_mongo import filtrar_canciones_genero
        filas = filtrar_canciones_genero(pk)
        canciones = [SimpleNamespace(
            pk=f.get('idCancion'),
            nombre_cancion=f.get('nombreCancion'),
            album=SimpleNamespace(
                titulo_album=f.get('tituloAlbum') or '—',
                artista=SimpleNamespace(nombre_artistico=f.get('nombreArtistico') or '—'),
            ),
        ) for f in filas]
        return render(request, self.template_name, {
            'genero': {'nombre': pk, 'pk': pk, 'nombre_genero': pk},
            'canciones': canciones[:50],
            'modo': 'detail',
        })


class AdminGeneroDeleteView(RequiereAdmin, View):
    def post(self, request, pk):
        eliminar_genero_mongo(pk)
        messages.success(request, f'Género "{pk}" eliminado de todas las canciones.')
        return redirect('catalogo:admin_genero_list')
