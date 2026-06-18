"""
CRUD de GeneroMusical para el administrador.

SPs usados:
  - Catalogo.SP_ListarGeneros
  - Catalogo.SP_CrearGenero
  - Catalogo.SP_EditarGenero
  - Catalogo.SP_EliminarGenero
"""

from django.views.generic import View
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import DatabaseError

from usuarios.mixins import RequiereAdmin
from ...models import GeneroMusical
from ...forms import GeneroForm
from ...services import (
    sp_listar_generos,
    sp_crear_genero,
    sp_editar_genero,
    sp_eliminar_genero,
)


class AdminGeneroListView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_genero.html'

    def get(self, request):
        busqueda = request.GET.get('q') or None
        generos = sp_listar_generos(busqueda=busqueda)
        return render(request, self.template_name, {
            'generos': generos, 'busqueda': busqueda or '',
            'modo': 'list',
        })


class AdminGeneroCreateView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_genero.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': GeneroForm(), 'modo': 'create',
        })

    def post(self, request):
        form = GeneroForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form, 'modo': 'create'})
        try:
            sp_crear_genero(form.cleaned_data['nombre_genero'])
            messages.success(request, 'Género creado.')
        except DatabaseError as e:
            messages.error(request, f'Error: {e}')
            return render(request, self.template_name, {'form': form, 'modo': 'create'})
        return redirect('catalogo:admin_genero_list')


class AdminGeneroUpdateView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_genero.html'

    def get(self, request, pk):
        g = get_object_or_404(GeneroMusical, pk=pk)
        form = GeneroForm(initial={'nombre_genero': g.nombre_genero})
        return render(request, self.template_name, {
            'form': form, 'genero': g, 'modo': 'update',
        })

    def post(self, request, pk):
        g = get_object_or_404(GeneroMusical, pk=pk)
        form = GeneroForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {
                'form': form, 'genero': g, 'modo': 'update',
            })
        try:
            sp_editar_genero(g.pk, form.cleaned_data['nombre_genero'])
            messages.success(request, 'Género actualizado.')
        except DatabaseError as e:
            messages.error(request, f'Error: {e}')
            return render(request, self.template_name, {
                'form': form, 'genero': g, 'modo': 'update',
            })
        return redirect('catalogo:admin_genero_list')


class AdminGeneroDetailView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_genero.html'

    def get(self, request, pk):
        g = get_object_or_404(GeneroMusical, pk=pk)
        # Canciones asociadas a este género
        from ...models import Cancion
        canciones = Cancion.objects.filter(
            cancion_generos__genero_musical=g,
        ).select_related('album', 'album__artista')[:50]
        return render(request, self.template_name, {
            'genero': g, 'canciones': canciones, 'modo': 'detail',
        })


class AdminGeneroDeleteView(RequiereAdmin, View):
    def post(self, request, pk):
        g = get_object_or_404(GeneroMusical, pk=pk)
        try:
            sp_eliminar_genero(g.pk)
            messages.success(request, f'Género "{g.nombre_genero}" eliminado.')
        except DatabaseError as e:
            messages.error(request, f'Error: {e}')
        return redirect('catalogo:admin_genero_list')
