"""
Vistas de Album para el ARTISTA.

SPs usados:
  - Catalogo.SP_ListarAlbumes       → ArtistaAlbumListView
  - Catalogo.SP_CrearAlbum          → ArtistaAlbumCreateView
  - Catalogo.SP_EditarAlbum         → ArtistaAlbumUpdateView
  - Catalogo.SP_DesactivarAlbum     → ArtistaAlbumDeactivateView
"""

from django.views.generic import ListView, View
from django.views.generic.edit import FormView
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.db import DatabaseError, transaction

from usuarios.mixins import RequiereArtista
from ...models import Album, Cancion, CancionGeneroMusical
from ...forms import AlbumCreateForm, AlbumUpdateForm
from ...services import (
    sp_crear_album,
    sp_editar_album,
    sp_listar_albumes,
    sp_desactivar_album,
)


# ──────────────────────────────────────────────────────────
# LIST
# ──────────────────────────────────────────────────────────
class ArtistaAlbumListView(RequiereArtista, View):
    template_name = 'catalogo/artista/artista_album.html'

    def get(self, request):
        artista_id = request.session['usuario_id']
        busqueda = request.GET.get('q') or None
        estado = request.GET.get('estado') or None

        # SP: SP_ListarAlbumes (defensivo: si falla el SP no rompemos
        # la pantalla, mostramos lista vacía con mensaje)
        try:
            albumes = sp_listar_albumes(
                artista_id=artista_id,
                estado=estado,
                busqueda=busqueda,
            )
        except DatabaseError as e:
            messages.error(request, f'No se pudo cargar el listado de álbumes: {e}')
            albumes = []

        return render(request, self.template_name, {
            'albumes': albumes,
            'busqueda': busqueda or '',
            'estado_actual': estado or '',
            'estados': Album.ESTADO_CHOICES,
            'modo': 'list',
        })


# ──────────────────────────────────────────────────────────
# CREATE
# ──────────────────────────────────────────────────────────
class ArtistaAlbumCreateView(RequiereArtista, FormView):
    template_name = 'catalogo/artista/artista_album.html'
    form_class = AlbumCreateForm
    success_url = reverse_lazy('catalogo:artista_album_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['modo'] = 'create'
        return ctx

    def form_valid(self, form):
        data = form.cleaned_data
        try:
            # SP: SP_CrearAlbum
            sp_crear_album(
                titulo=data['titulo_album'],
                fecha_lanzamiento=data['fecha_lanzamiento_album'],
                descripcion=data.get('descripcion_album') or '',
                tipo_album_id=data['tipo_album'].pk,
                artista_id=self.request.session['usuario_id'],
            )
            messages.success(self.request, 'Álbum creado correctamente.')
        except DatabaseError as e:
            messages.error(self.request, f'Error al crear el álbum: {e}')
            return self.form_invalid(form)
        return super().form_valid(form)


# ──────────────────────────────────────────────────────────
# DETAIL · ver el álbum (solo lectura) + sus canciones
# ──────────────────────────────────────────────────────────
class ArtistaAlbumDetailView(RequiereArtista, View):
    template_name = 'catalogo/artista/artista_album.html'

    def get(self, request, pk):
        from ...models import Cancion
        artista_id = request.session['usuario_id']
        album = get_object_or_404(
            Album.objects.select_related('tipo_album', 'artista'),
            pk=pk, artista_id=artista_id,
        )
        canciones = Cancion.objects.filter(album=album).order_by('numero_pista')
        return render(request, self.template_name, {
            'album': album,
            'canciones': canciones,
            'modo': 'detail',
        })


# ──────────────────────────────────────────────────────────
# UPDATE
# ──────────────────────────────────────────────────────────
class ArtistaAlbumUpdateView(RequiereArtista, View):
    template_name = 'catalogo/artista/artista_album.html'

    def _get_album(self, pk, artista_id):
        """Carga un álbum garantizando que sea del artista logueado."""
        return get_object_or_404(Album, pk=pk, artista_id=artista_id)

    def get(self, request, pk):
        artista_id = request.session['usuario_id']
        album = self._get_album(pk, artista_id)
        form = AlbumUpdateForm(instance=album)
        return render(request, self.template_name, {
            'form': form,
            'album': album,
            'modo': 'update',
        })

    def post(self, request, pk):
        artista_id = request.session['usuario_id']
        album = self._get_album(pk, artista_id)
        form = AlbumUpdateForm(request.POST, instance=album)
        if not form.is_valid():
            return render(request, self.template_name, {
                'form': form, 'album': album, 'modo': 'update',
            })
        data = form.cleaned_data
        try:
            # SP: SP_EditarAlbum (con artista_id → valida ownership)
            sp_editar_album(
                id_album=album.pk,
                titulo=data['titulo_album'],
                fecha_lanzamiento=data['fecha_lanzamiento_album'],
                descripcion=data.get('descripcion_album') or '',
                tipo_album_id=data['tipo_album'].pk,
                estado=None,
                artista_id=artista_id,
            )
            messages.success(request, 'Álbum actualizado.')
        except DatabaseError as e:
            messages.error(request, f'Error al editar: {e}')
            return render(request, self.template_name, {
                'form': form, 'album': album, 'modo': 'update',
            })
        return redirect('catalogo:artista_album_list')


# ──────────────────────────────────────────────────────────
# DEACTIVATE (soft delete)
# ──────────────────────────────────────────────────────────
class ArtistaAlbumDeactivateView(RequiereArtista, View):
    def post(self, request, pk):
        artista_id = request.session['usuario_id']
        # Garantizar ownership antes de pasar al SP
        album = get_object_or_404(Album, pk=pk, artista_id=artista_id)
        try:
            sp_desactivar_album(id_album=album.pk, ejecutor_id=artista_id)
            messages.success(request, f'Álbum "{album.titulo_album}" desactivado.')
        except DatabaseError as e:
            messages.error(request, f'Error al desactivar: {e}')
        return redirect('catalogo:artista_album_list')


# ──────────────────────────────────────────────────────────
# DELETE (hard delete) · elimina el álbum permanentemente
# A diferencia de "desactivar" (estado → inactivo), esto borra
# el registro. Se eliminan en una transacción las canciones del
# álbum y sus géneros asociados. Si existen datos que impiden el
# borrado (reproducciones, likes, listas…), la BD lo bloquea y se
# informa al artista para que use "Desactivar" en su lugar.
# ──────────────────────────────────────────────────────────
class ArtistaAlbumDeleteView(RequiereArtista, View):
    def post(self, request, pk):
        artista_id = request.session['usuario_id']
        # Garantizar que el álbum sea del artista logueado.
        album = get_object_or_404(Album, pk=pk, artista_id=artista_id)
        titulo = album.titulo_album
        try:
            with transaction.atomic():
                canciones = Cancion.objects.filter(album=album)
                # 1) Quitar relaciones M:N de género de esas canciones.
                CancionGeneroMusical.objects.filter(cancion__in=canciones).delete()
                # 2) Eliminar las canciones del álbum.
                canciones.delete()
                # 3) Eliminar el álbum.
                album.delete()
            messages.success(request, f'Álbum "{titulo}" eliminado permanentemente.')
        except DatabaseError:
            messages.error(
                request,
                f'No se pudo eliminar "{titulo}" porque tiene datos asociados '
                f'(reproducciones, "me gusta" o listas de reproducción). '
                f'Usa la opción "Desactivar" en su lugar.'
            )
        return redirect('catalogo:artista_album_list')
