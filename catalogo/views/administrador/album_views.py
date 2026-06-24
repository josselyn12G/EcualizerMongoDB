"""
Vistas de Album para el ADMINISTRADOR — migradas a MongoDB.
"""

from django.views.generic import View
from django.shortcuts import render, redirect
from django.contrib import messages

from usuarios.mixins import RequiereAdmin
from ...forms.mongo_forms import MongoAlbumAdminForm, AlbumReporteForm
from ...services.catalogo_mongo import catalogo_tipos_album
from ...services.catalogo_mongo import (
    listar_albumes,
    get_album_ns,
    get_album_detalle,
    actualizar_album,
    desactivar_album,
)


# ──────────────────────────────────────────────────────────
# LIST
# ──────────────────────────────────────────────────────────
class AdminAlbumListView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_album.html'

    def get(self, request):
        busqueda = request.GET.get('q') or None
        estado = request.GET.get('estado') or None
        albumes = listar_albumes(artista_id=None, estado=estado, busqueda=busqueda)
        return render(request, self.template_name, {
            'albumes': albumes,
            'busqueda': busqueda or '',
            'estado_actual': estado or '',
            'estados': [('activo', 'Activo'), ('inactivo', 'Inactivo'), ('eliminado', 'Eliminado')],
            'modo': 'list',
        })


# ──────────────────────────────────────────────────────────
# DETAIL
# ──────────────────────────────────────────────────────────
class AdminAlbumDetailView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_album.html'

    def get(self, request, pk):
        result = get_album_detalle(pk)
        if not result:
            messages.error(request, 'Álbum no encontrado.')
            return redirect('catalogo:admin_album_list')
        album, canciones = result
        return render(request, self.template_name, {
            'album': album, 'canciones': canciones, 'modo': 'detail',
        })


# ──────────────────────────────────────────────────────────
# UPDATE
# ──────────────────────────────────────────────────────────
class AdminAlbumUpdateView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_album.html'

    def get(self, request, pk):
        album = get_album_ns(pk)
        if not album:
            messages.error(request, 'Álbum no encontrado.')
            return redirect('catalogo:admin_album_list')
        form = MongoAlbumAdminForm(initial={
            'titulo': album.titulo_album,
            'fecha_lanzamiento': album.fecha_lanzamiento_album,
            'tipo': getattr(album.tipo_album, 'nombre_tipo', 'Album'),
            'descripcion': album.descripcion_album or '',
            'estado': album.estado_album,
        }, tipo_choices=catalogo_tipos_album())
        return render(request, self.template_name, {
            'form': form, 'album': album, 'modo': 'update',
        })

    def post(self, request, pk):
        album = get_album_ns(pk)
        if not album:
            messages.error(request, 'Álbum no encontrado.')
            return redirect('catalogo:admin_album_list')
        form = MongoAlbumAdminForm(request.POST, tipo_choices=catalogo_tipos_album())
        if not form.is_valid():
            return render(request, self.template_name, {
                'form': form, 'album': album, 'modo': 'update',
            })
        d = form.cleaned_data
        actualizar_album(
            pk=pk,
            titulo=d['titulo'],
            fecha=d['fecha_lanzamiento'],
            descripcion=d.get('descripcion') or '',
            tipo=d['tipo'],
            estado=d.get('estado'),
        )
        messages.success(request, 'Álbum actualizado por el admin.')
        return redirect('catalogo:admin_album_list')


# ──────────────────────────────────────────────────────────
# REPORT / DEACTIVATE
# ──────────────────────────────────────────────────────────
class AdminAlbumReportView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_album.html'

    def get(self, request, pk):
        album = get_album_ns(pk)
        if not album:
            return redirect('catalogo:admin_album_list')
        form = AlbumReporteForm()
        return render(request, self.template_name, {
            'form': form, 'album': album, 'modo': 'report',
        })

    def post(self, request, pk):
        album = get_album_ns(pk)
        if not album:
            return redirect('catalogo:admin_album_list')
        form = AlbumReporteForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {
                'form': form, 'album': album, 'modo': 'report',
            })
        titulo = desactivar_album(pk)
        messages.success(
            request,
            f'Álbum "{titulo}" reportado y desactivado. Motivo: {form.cleaned_data["motivo"]}'
        )
        return redirect('catalogo:admin_album_list')
