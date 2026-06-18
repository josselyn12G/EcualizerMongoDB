"""
Vistas de Album para el ADMINISTRADOR.

SPs usados:
  - Catalogo.SP_ListarAlbumes      → AdminAlbumListView (sin filtro de artista)
  - Catalogo.SP_EditarAlbum        → AdminAlbumUpdateView (cambia estado)
  - Catalogo.SP_DesactivarAlbum    → AdminAlbumUpdateView (acción "desactivar")
"""

from django.views.generic import View
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import DatabaseError

from usuarios.mixins import RequiereAdmin
from ...models import Album, Cancion
from ...forms import AlbumAdminUpdateForm, AlbumReportForm
from ...services import (
    sp_listar_albumes,
    sp_editar_album,
    sp_desactivar_album,
)


# ──────────────────────────────────────────────────────────
# LIST · ve todos los álbumes (todos los estados)
# ──────────────────────────────────────────────────────────
class AdminAlbumListView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_album.html'

    def get(self, request):
        busqueda = request.GET.get('q') or None
        estado = request.GET.get('estado') or None
        # SP: SP_ListarAlbumes (sin filtro de artista → admin ve todos)
        albumes = sp_listar_albumes(
            artista_id=None,
            estado=estado,
            busqueda=busqueda,
        )
        return render(request, self.template_name, {
            'albumes': albumes,
            'busqueda': busqueda or '',
            'estado_actual': estado or '',
            'estados': Album.ESTADO_CHOICES,
            'modo': 'list',
        })


# ──────────────────────────────────────────────────────────
# UPDATE (admin)
# ──────────────────────────────────────────────────────────
class AdminAlbumUpdateView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_album.html'

    def get(self, request, pk):
        album = get_object_or_404(Album, pk=pk)
        form = AlbumAdminUpdateForm(instance=album)
        return render(request, self.template_name, {
            'form': form, 'album': album, 'modo': 'update',
        })

    def post(self, request, pk):
        album = get_object_or_404(Album, pk=pk)
        form = AlbumAdminUpdateForm(request.POST, instance=album)
        if not form.is_valid():
            return render(request, self.template_name, {
                'form': form, 'album': album, 'modo': 'update',
            })
        data = form.cleaned_data
        try:
            # SP: SP_EditarAlbum (sin artista_id → admin pasa NULL)
            sp_editar_album(
                id_album=album.pk,
                titulo=data['titulo_album'],
                fecha_lanzamiento=data['fecha_lanzamiento_album'],
                descripcion=data.get('descripcion_album') or '',
                tipo_album_id=data['tipo_album'].pk,
                estado=data['estado_album'],
                artista_id=None,
            )
            messages.success(request, 'Álbum actualizado por el admin.')
        except DatabaseError as e:
            messages.error(request, f'Error: {e}')
            return render(request, self.template_name, {
                'form': form, 'album': album, 'modo': 'update',
            })
        return redirect('catalogo:admin_album_list')


# ──────────────────────────────────────────────────────────
# DETAIL · Ver detalle del álbum (incluye canciones)
# ──────────────────────────────────────────────────────────
class AdminAlbumDetailView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_album.html'

    def get(self, request, pk):
        album = get_object_or_404(
            Album.objects.select_related('artista', 'tipo_album'),
            pk=pk,
        )
        canciones = Cancion.objects.filter(album=album).order_by('numero_pista')
        return render(request, self.template_name, {
            'album': album, 'canciones': canciones, 'modo': 'detail',
        })


# ──────────────────────────────────────────────────────────
# REPORT / DEACTIVATE
# ──────────────────────────────────────────────────────────
class AdminAlbumReportView(RequiereAdmin, View):
    """
    El admin "reporta" un álbum: lo desactiva y envía comentario.
    Aquí reusamos SP_DesactivarAlbum y guardamos el reporte
    como un mensaje al artista.
    """
    template_name = 'catalogo/administrador/admin_album.html'

    def get(self, request, pk):
        album = get_object_or_404(Album, pk=pk)
        form = AlbumReportForm()
        return render(request, self.template_name, {
            'form': form, 'album': album, 'modo': 'report',
        })

    def post(self, request, pk):
        album = get_object_or_404(Album, pk=pk)
        form = AlbumReportForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {
                'form': form, 'album': album, 'modo': 'report',
            })
        admin_id = request.session['usuario_id']
        try:
            sp_desactivar_album(id_album=album.pk, ejecutor_id=admin_id)
            # NOTA: el comentario se guarda en messages framework por ahora.
            # Cuando exista la tabla Catalogo.ReporteAlbum, llamar a un SP.
            messages.success(
                request,
                f'Álbum reportado y desactivado. Motivo: {form.cleaned_data["motivo"]}'
            )
        except DatabaseError as e:
            messages.error(request, f'Error: {e}')
            return render(request, self.template_name, {
                'form': form, 'album': album, 'modo': 'report',
            })
        return redirect('catalogo:admin_album_list')
