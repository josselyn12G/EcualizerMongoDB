"""
Vistas de Cancion para el ARTISTA.

SPs usados:
  - Catalogo.SP_ListarCanciones                   → ArtistaCancionListView
  - Analitica.sp_ReporteReproduccionesPorCancion  → ArtistaCancionListView (KPI)
  - Catalogo.SP_CrearCancion                      → ArtistaCancionCreateView
  - Catalogo.SP_EditarCancion                     → ArtistaCancionUpdateView
  - Catalogo.SP_DesactivarCancion                 → ArtistaCancionDeactivateView
"""

from django.views.generic import View
from django.views.generic.edit import FormView
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import DatabaseError

from usuarios.mixins import RequiereArtista
from ...models import Cancion, Album, GeneroMusical
from ...forms import CancionCreateForm, CancionUpdateForm
from ...services import (
    sp_crear_cancion,
    sp_editar_cancion,
    sp_listar_canciones,
    sp_desactivar_cancion,
    sp_reporte_reproducciones_por_cancion,
)


# ──────────────────────────────────────────────────────────
# LIST
# ──────────────────────────────────────────────────────────
class ArtistaCancionListView(RequiereArtista, View):
    template_name = 'catalogo/artista/artista_cancion.html'

    def get(self, request):
        artista_id = request.session['usuario_id']
        busqueda = request.GET.get('q') or None
        album_id = request.GET.get('album') or None
        estado = request.GET.get('estado') or None

        # SP: SP_ListarCanciones (defensivo: si el SP no existe aún o
        # devuelve error, no rompemos la pantalla)
        try:
            canciones = sp_listar_canciones(
                artista_id=artista_id,
                album_id=album_id,
                estado=estado,
                busqueda=busqueda,
            )
        except DatabaseError as e:
            messages.error(request, f'No se pudo cargar el listado de canciones: {e}')
            canciones = []

        # SP existente: sp_ReporteReproduccionesPorCancion (KPI)
        try:
            reproducciones = sp_reporte_reproducciones_por_cancion(
                id_artista=artista_id,
                id_album=album_id,
                periodo='mes',
            )
        except DatabaseError:
            reproducciones = []

        # Álbumes del artista para el filtro
        try:
            albumes_del_artista = list(Album.objects.filter(
                artista_id=artista_id,
                estado_album='activo',
            ))
        except DatabaseError:
            albumes_del_artista = []

        return render(request, self.template_name, {
            'canciones': canciones,
            'reproducciones_mes': reproducciones,
            'albumes': albumes_del_artista,
            'busqueda': busqueda or '',
            'album_id': int(album_id) if album_id else '',
            'estado_actual': estado or '',
            'estados': Cancion.ESTADO_CHOICES,
            'modo': 'list',
        })


# ──────────────────────────────────────────────────────────
# CREATE
# ──────────────────────────────────────────────────────────
class ArtistaCancionCreateView(RequiereArtista, View):
    template_name = 'catalogo/artista/artista_cancion.html'

    def get(self, request):
        artista_id = request.session['usuario_id']
        form = CancionCreateForm(artista_id=artista_id)
        return render(request, self.template_name, {
            'form': form,
            'modo': 'create',
            'all_generos': list(GeneroMusical.objects.all()),
            'generos_actuales_ids': set(),
        })

    def post(self, request):
        artista_id = request.session['usuario_id']
        form = CancionCreateForm(request.POST, artista_id=artista_id)
        # IDs que vinieron del front (chips activos) — para repintar si falla
        seleccionados = set(int(x) for x in request.POST.getlist('generos') if x.isdigit())
        if not form.is_valid():
            return render(request, self.template_name, {
                'form': form, 'modo': 'create',
                'all_generos': list(GeneroMusical.objects.all()),
                'generos_actuales_ids': seleccionados,
            })

        data = form.cleaned_data
        try:
            # SP: SP_CrearCancion
            sp_crear_cancion(
                nombre=data['nombre_cancion'],
                duracion=data['duracion'],
                fecha_lanzamiento=data['fecha_lanzamiento'],
                calidad_kbps=data['calidad_kbps'],
                letra=data.get('letra_cancion') or '',
                album_id=data['album'].pk,
                numero_pista=data['numero_pista'],
                generos_ids=[g.pk for g in data.get('generos', [])],
            )
            messages.success(request, 'Canción creada correctamente.')
        except DatabaseError as e:
            messages.error(request, f'Error al crear canción: {e}')
            return render(request, self.template_name, {
                'form': form, 'modo': 'create',
                'all_generos': list(GeneroMusical.objects.all()),
                'generos_actuales_ids': seleccionados,
            })
        return redirect('catalogo:artista_cancion_list')


# ──────────────────────────────────────────────────────────
# UPDATE
# ──────────────────────────────────────────────────────────
class ArtistaCancionUpdateView(RequiereArtista, View):
    template_name = 'catalogo/artista/artista_cancion.html'

    def _get_cancion(self, pk, artista_id):
        cancion = get_object_or_404(Cancion, pk=pk)
        if cancion.album.artista_id != artista_id:
            from django.http import Http404
            raise Http404('No tienes acceso a esta canción.')
        return cancion

    def get(self, request, pk):
        artista_id = request.session['usuario_id']
        cancion = self._get_cancion(pk, artista_id)
        form = CancionUpdateForm(instance=cancion, artista_id=artista_id)
        actuales = set(cancion.generos.values_list('pk', flat=True))
        return render(request, self.template_name, {
            'form': form, 'cancion': cancion, 'modo': 'update',
            'all_generos': list(GeneroMusical.objects.all()),
            'generos_actuales_ids': actuales,
        })

    def post(self, request, pk):
        artista_id = request.session['usuario_id']
        cancion = self._get_cancion(pk, artista_id)
        form = CancionUpdateForm(request.POST, instance=cancion, artista_id=artista_id)
        seleccionados = set(int(x) for x in request.POST.getlist('generos') if x.isdigit())
        if not form.is_valid():
            return render(request, self.template_name, {
                'form': form, 'cancion': cancion, 'modo': 'update',
                'all_generos': list(GeneroMusical.objects.all()),
                'generos_actuales_ids': seleccionados,
            })
        data = form.cleaned_data
        try:
            # SP: SP_EditarCancion (artista_id → valida ownership)
            sp_editar_cancion(
                id_cancion=cancion.pk,
                nombre=data['nombre_cancion'],
                duracion=data['duracion'],
                fecha_lanzamiento=data['fecha_lanzamiento'],
                calidad_kbps=data['calidad_kbps'],
                letra=data.get('letra_cancion') or '',
                numero_pista=data['numero_pista'],
                estado=None,
                generos_ids=[g.pk for g in data.get('generos', [])],
                artista_id=artista_id,
            )
            messages.success(request, 'Canción actualizada.')
        except DatabaseError as e:
            messages.error(request, f'Error al editar: {e}')
            return render(request, self.template_name, {
                'form': form, 'cancion': cancion, 'modo': 'update',
                'all_generos': list(GeneroMusical.objects.all()),
                'generos_actuales_ids': seleccionados,
            })
        return redirect('catalogo:artista_cancion_list')


# ──────────────────────────────────────────────────────────
# DEACTIVATE
# ──────────────────────────────────────────────────────────
class ArtistaCancionDeactivateView(RequiereArtista, View):
    def post(self, request, pk):
        artista_id = request.session['usuario_id']
        cancion = get_object_or_404(Cancion, pk=pk)
        if cancion.album.artista_id != artista_id:
            messages.error(request, 'No puedes desactivar canciones de otros artistas.')
            return redirect('catalogo:artista_cancion_list')
        try:
            sp_desactivar_cancion(id_cancion=cancion.pk, ejecutor_id=artista_id)
            messages.success(request, f'Canción "{cancion.nombre_cancion}" desactivada.')
        except DatabaseError as e:
            messages.error(request, f'Error: {e}')
        return redirect('catalogo:artista_cancion_list')
