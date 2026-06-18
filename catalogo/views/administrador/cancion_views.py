"""
Vistas de Cancion para el ADMINISTRADOR.

SPs usados:
  - Catalogo.SP_ListarCancionesConGeneros         → AdminCancionListView (badges de género)
  - Analitica.sp_RankingGlobalCanciones           → AdminCancionListView (top 20 global)
  - Catalogo.SP_EditarCancion                     → AdminCancionUpdateView
  - Catalogo.SP_DesactivarCancion                 → AdminCancionDeactivateView
  - Catalogo.SP_ReportarCancion                   → AdminCancionReportView
  - Catalogo.SP_GenerosDeCancion                  → AdminCancionDetail/UpdateView (chips)
  - Catalogo.SP_AgregarGeneroACancion             → AdminCancionGeneroAddView
  - Catalogo.SP_QuitarGeneroDeCancion             → AdminCancionGeneroRemoveView
"""

from django.views.generic import View
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import DatabaseError

from usuarios.mixins import RequiereAdmin
from ...models import Cancion, GeneroMusical
from ...forms import CancionAdminUpdateForm, CancionReportForm
from ...services import (
    sp_editar_cancion,
    sp_desactivar_cancion,
    sp_reportar_cancion,
    sp_ranking_global_canciones,
    sp_listar_canciones_con_generos,
    sp_generos_de_cancion,
    sp_agregar_genero_a_cancion,
    sp_quitar_genero_de_cancion,
)


# ──────────────────────────────────────────────────────────
# LIST · todas las canciones + ranking global + badges de género
# ──────────────────────────────────────────────────────────
class AdminCancionListView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_cancion.html'

    def get(self, request):
        busqueda = request.GET.get('q') or None
        estado = request.GET.get('estado') or None

        # SP: SP_ListarCancionesConGeneros (incluye generosCSV)
        canciones = sp_listar_canciones_con_generos(
            artista_id=None, album_id=None,
            estado=estado, busqueda=busqueda,
        )

        # SP existente: sp_RankingGlobalCanciones
        try:
            ranking = sp_ranking_global_canciones(periodo='mes')
        except DatabaseError:
            ranking = []

        return render(request, self.template_name, {
            'canciones': canciones,
            'ranking_global': ranking,
            'busqueda': busqueda or '',
            'estado_actual': estado or '',
            'estados': Cancion.ESTADO_CHOICES,
            'modo': 'list',
        })


# ──────────────────────────────────────────────────────────
# DETAIL · Ver canción
# ──────────────────────────────────────────────────────────
class AdminCancionDetailView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_cancion.html'

    def get(self, request, pk):
        cancion = get_object_or_404(
            Cancion.objects.select_related('album', 'album__artista', 'album__tipo_album'),
            pk=pk,
        )
        # SP: SP_GenerosDeCancion
        generos_asignados = sp_generos_de_cancion(cancion.pk)
        return render(request, self.template_name, {
            'cancion': cancion,
            'generos_asignados': generos_asignados,
            'modo': 'detail',
        })


# ──────────────────────────────────────────────────────────
# UPDATE (admin) · sin editar géneros directamente
# ──────────────────────────────────────────────────────────
class AdminCancionUpdateView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_cancion.html'

    def get(self, request, pk):
        cancion = get_object_or_404(Cancion, pk=pk)
        form = CancionAdminUpdateForm(instance=cancion)
        # SP: SP_GenerosDeCancion
        generos_asignados = sp_generos_de_cancion(cancion.pk)
        # Géneros NO asignados (para el dropdown "Agregar")
        ids_asignados = {g['idGeneroMusical'] for g in generos_asignados}
        generos_disponibles = GeneroMusical.objects.exclude(pk__in=ids_asignados)
        return render(request, self.template_name, {
            'form': form, 'cancion': cancion,
            'generos_asignados': generos_asignados,
            'generos_disponibles': generos_disponibles,
            'modo': 'update',
        })

    def post(self, request, pk):
        cancion = get_object_or_404(Cancion, pk=pk)
        form = CancionAdminUpdateForm(request.POST, instance=cancion)
        if not form.is_valid():
            generos_asignados = sp_generos_de_cancion(cancion.pk)
            ids_asignados = {g['idGeneroMusical'] for g in generos_asignados}
            return render(request, self.template_name, {
                'form': form, 'cancion': cancion,
                'generos_asignados': generos_asignados,
                'generos_disponibles': GeneroMusical.objects.exclude(pk__in=ids_asignados),
                'modo': 'update',
            })
        data = form.cleaned_data
        try:
            # NOTA: no enviamos generos=... porque se gestionan aparte
            sp_editar_cancion(
                id_cancion=cancion.pk,
                nombre=data['nombre_cancion'],
                duracion=data['duracion'],
                fecha_lanzamiento=data['fecha_lanzamiento'],
                calidad_kbps=data['calidad_kbps'],
                letra=data.get('letra_cancion') or '',
                numero_pista=data['numero_pista'],
                estado=data['estado_cancion'],
                generos_ids=None,        # NO tocamos M:N en este SP
                artista_id=None,
            )
            messages.success(request, 'Canción actualizada.')
        except DatabaseError as e:
            messages.error(request, f'Error: {e}')
            return redirect('catalogo:admin_cancion_update', pk=cancion.pk)
        return redirect('catalogo:admin_cancion_list')


# ──────────────────────────────────────────────────────────
# M:N · Añadir / Quitar género de la canción
# ──────────────────────────────────────────────────────────
class AdminCancionGeneroAddView(RequiereAdmin, View):
    """POST · agrega un género a la canción."""

    def post(self, request, pk):
        try:
            genero_id = int(request.POST.get('genero_id', 0))
        except (TypeError, ValueError):
            messages.error(request, 'Género inválido.')
            return redirect('catalogo:admin_cancion_update', pk=pk)

        if not genero_id:
            messages.error(request, 'Selecciona un género.')
            return redirect('catalogo:admin_cancion_update', pk=pk)

        try:
            sp_agregar_genero_a_cancion(pk, genero_id)
            messages.success(request, 'Género agregado.')
        except DatabaseError as e:
            messages.error(request, f'Error: {e}')
        return redirect('catalogo:admin_cancion_update', pk=pk)


class AdminCancionGeneroRemoveView(RequiereAdmin, View):
    """POST · quita un género de la canción."""

    def post(self, request, pk, genero_id):
        try:
            sp_quitar_genero_de_cancion(pk, genero_id)
            messages.success(request, 'Género eliminado de la canción.')
        except DatabaseError as e:
            messages.error(request, f'Error: {e}')
        return redirect('catalogo:admin_cancion_update', pk=pk)


# ──────────────────────────────────────────────────────────
# DEACTIVATE rápido
# ──────────────────────────────────────────────────────────
class AdminCancionDeactivateView(RequiereAdmin, View):
    def post(self, request, pk):
        cancion = get_object_or_404(Cancion, pk=pk)
        admin_id = request.session['usuario_id']
        try:
            sp_desactivar_cancion(id_cancion=cancion.pk, ejecutor_id=admin_id)
            messages.success(request, f'Canción "{cancion.nombre_cancion}" desactivada.')
        except DatabaseError as e:
            messages.error(request, f'Error: {e}')
        return redirect('catalogo:admin_cancion_list')


# ──────────────────────────────────────────────────────────
# REPORT
# ──────────────────────────────────────────────────────────
class AdminCancionReportView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_cancion.html'

    def get(self, request, pk):
        cancion = get_object_or_404(Cancion, pk=pk)
        form = CancionReportForm()
        return render(request, self.template_name, {
            'form': form, 'cancion': cancion, 'modo': 'report',
        })

    def post(self, request, pk):
        cancion = get_object_or_404(Cancion, pk=pk)
        form = CancionReportForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {
                'form': form, 'cancion': cancion, 'modo': 'report',
            })
        admin_id = request.session['usuario_id']
        try:
            sp_reportar_cancion(
                id_cancion=cancion.pk, admin_id=admin_id,
                motivo=form.cleaned_data['motivo'],
                comentario=form.cleaned_data['comentario'],
            )
            messages.success(request, 'Reporte enviado al artista.')
        except DatabaseError as e:
            messages.error(request, f'Error: {e}')
            return render(request, self.template_name, {
                'form': form, 'cancion': cancion, 'modo': 'report',
            })
        return redirect('catalogo:admin_cancion_list')
