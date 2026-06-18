"""
CRUD de TipoAlbum para el administrador.

SPs usados:
  - Catalogo.SP_ListarTiposAlbum
  - Catalogo.SP_CrearTipoAlbum
  - Catalogo.SP_EditarTipoAlbum
  - Catalogo.SP_EliminarTipoAlbum
"""

from django.views.generic import View
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import DatabaseError

from usuarios.mixins import RequiereAdmin
from ...models import TipoAlbum, Album
from ...forms import TipoAlbumForm
from ...services import (
    sp_listar_tipos_album,
    sp_crear_tipo_album,
    sp_editar_tipo_album,
    sp_eliminar_tipo_album,
)


class AdminTipoAlbumListView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_tipo_album.html'

    def get(self, request):
        busqueda = request.GET.get('q') or None
        tipos = sp_listar_tipos_album(busqueda=busqueda)
        return render(request, self.template_name, {
            'tipos': tipos, 'busqueda': busqueda or '',
            'modo': 'list',
        })


class AdminTipoAlbumCreateView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_tipo_album.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': TipoAlbumForm(), 'modo': 'create',
        })

    def post(self, request):
        form = TipoAlbumForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form, 'modo': 'create'})
        try:
            sp_crear_tipo_album(
                nombre_tipo=form.cleaned_data['nombre_tipo'],
                descripcion=form.cleaned_data.get('descripcion_tipo') or None,
            )
            messages.success(request, 'Tipo de álbum creado.')
        except DatabaseError as e:
            messages.error(request, f'Error: {e}')
            return render(request, self.template_name, {'form': form, 'modo': 'create'})
        return redirect('catalogo:admin_tipo_album_list')


class AdminTipoAlbumUpdateView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_tipo_album.html'

    def get(self, request, pk):
        t = get_object_or_404(TipoAlbum, pk=pk)
        form = TipoAlbumForm(initial={
            'nombre_tipo': t.nombre_tipo,
            'descripcion_tipo': t.descripcion_tipo,
        })
        return render(request, self.template_name, {
            'form': form, 'tipo': t, 'modo': 'update',
        })

    def post(self, request, pk):
        t = get_object_or_404(TipoAlbum, pk=pk)
        form = TipoAlbumForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {
                'form': form, 'tipo': t, 'modo': 'update',
            })
        try:
            sp_editar_tipo_album(
                id_tipo=t.pk,
                nombre_tipo=form.cleaned_data['nombre_tipo'],
                descripcion=form.cleaned_data.get('descripcion_tipo') or None,
            )
            messages.success(request, 'Tipo de álbum actualizado.')
        except DatabaseError as e:
            messages.error(request, f'Error: {e}')
            return render(request, self.template_name, {
                'form': form, 'tipo': t, 'modo': 'update',
            })
        return redirect('catalogo:admin_tipo_album_list')


class AdminTipoAlbumDetailView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_tipo_album.html'

    def get(self, request, pk):
        t = get_object_or_404(TipoAlbum, pk=pk)
        albumes = Album.objects.filter(tipo_album=t).select_related('artista')[:50]
        return render(request, self.template_name, {
            'tipo': t, 'albumes': albumes, 'modo': 'detail',
        })


class AdminTipoAlbumDeleteView(RequiereAdmin, View):
    def post(self, request, pk):
        t = get_object_or_404(TipoAlbum, pk=pk)
        try:
            sp_eliminar_tipo_album(t.pk)
            messages.success(request, f'Tipo "{t.nombre_tipo}" eliminado.')
        except DatabaseError as e:
            messages.error(request, f'Error: {e}')
        return redirect('catalogo:admin_tipo_album_list')
