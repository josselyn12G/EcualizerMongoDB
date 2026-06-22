"""
CRUD de TipoAlbum para el administrador — MongoDB (tipos embebidos en Albums).
"""

from django import forms
from django.views.generic import View
from django.shortcuts import render, redirect
from django.contrib import messages

from usuarios.mixins import RequiereAdmin
from ...services.catalogo_mongo import (
    listar_tipos_album_mongo,
    renombrar_tipo_album_mongo,
    agregar_tipo_album_mongo,
    listar_albumes,
)


class _TipoAlbumForm(forms.Form):
    nombre_tipo = forms.CharField(
        label='Nombre del tipo', max_length=40,
        widget=forms.TextInput(attrs={'class': 'field-input form-control'}),
    )
    descripcion_tipo = forms.CharField(
        label='Descripción', required=False,
        widget=forms.Textarea(attrs={'class': 'field-textarea form-control', 'rows': 2}),
    )


class AdminTipoAlbumListView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_tipo_album.html'

    def get(self, request):
        busqueda = request.GET.get('q') or None
        tipos = listar_tipos_album_mongo(busqueda=busqueda)
        return render(request, self.template_name, {
            'tipos': tipos, 'busqueda': busqueda or '', 'modo': 'list',
        })


class AdminTipoAlbumCreateView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_tipo_album.html'

    def get(self, request):
        return render(request, self.template_name, {
            'form': _TipoAlbumForm(), 'modo': 'create',
        })

    def post(self, request):
        form = _TipoAlbumForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form, 'modo': 'create'})
        nombre = form.cleaned_data['nombre_tipo'].strip()
        if agregar_tipo_album_mongo(nombre):
            messages.success(request, f'Tipo "{nombre}" disponible para nuevos álbumes.')
        else:
            messages.warning(request, f'El tipo "{nombre}" ya existe.')
        return redirect('catalogo:admin_tipo_album_list')


class AdminTipoAlbumUpdateView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_tipo_album.html'

    def get(self, request, pk):
        form = _TipoAlbumForm(initial={'nombre_tipo': pk})
        return render(request, self.template_name, {
            'form': form, 'tipo': {'nombre_tipo': pk}, 'modo': 'update',
        })

    def post(self, request, pk):
        form = _TipoAlbumForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {
                'form': form, 'tipo': {'nombre_tipo': pk}, 'modo': 'update',
            })
        nuevo = form.cleaned_data['nombre_tipo'].strip()
        renombrar_tipo_album_mongo(pk, nuevo)
        messages.success(request, f'Tipo renombrado de "{pk}" a "{nuevo}".')
        return redirect('catalogo:admin_tipo_album_list')


class AdminTipoAlbumDetailView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_tipo_album.html'

    def get(self, request, pk):
        albumes = listar_albumes()
        albumes_filtrados = [a for a in albumes if a.get('nombreTipo') == pk]
        return render(request, self.template_name, {
            'tipo': {'nombre_tipo': pk},
            'albumes': albumes_filtrados[:50],
            'modo': 'detail',
        })


class AdminTipoAlbumDeleteView(RequiereAdmin, View):
    def post(self, request, pk):
        messages.info(
            request,
            f'El tipo "{pk}" se eliminará de los álbumes al editarlos individualmente. '
            f'En MongoDB los tipos son campos embebidos.'
        )
        return redirect('catalogo:admin_tipo_album_list')
