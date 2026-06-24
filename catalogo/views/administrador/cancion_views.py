"""
Vistas de Cancion para el ADMINISTRADOR — migradas a MongoDB.
"""

from django.views.generic import View
from django.shortcuts import render, redirect
from django.contrib import messages

from usuarios.mixins import RequiereAdmin
from ...forms.mongo_forms import MongoCancionAdminEditForm
from ...services.cancion_mongo import (
    listar_canciones,
    ranking_canciones_mes,
    get_cancion_ns,
    actualizar_cancion,
    desactivar_cancion,
    agregar_genero_cancion,
    quitar_genero_cancion,
)
from ...services.catalogo_mongo import catalogo_generos


# ──────────────────────────────────────────────────────────
# LIST
# ──────────────────────────────────────────────────────────
class AdminCancionListView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_cancion.html'

    def get(self, request):
        busqueda = request.GET.get('q') or None
        estado = request.GET.get('estado') or None
        canciones = listar_canciones(estado=estado, busqueda=busqueda)
        try:
            ranking = ranking_canciones_mes(20)
        except Exception:
            ranking = []
        return render(request, self.template_name, {
            'canciones': canciones,
            'ranking_global': ranking,
            'busqueda': busqueda or '',
            'estado_actual': estado or '',
            'estados': [('activa', 'Activa'), ('inactiva', 'Inactiva'),
                        ('bloqueada', 'Bloqueada'), ('eliminada', 'Eliminada')],
            'modo': 'list',
        })


# ──────────────────────────────────────────────────────────
# DETAIL
# ──────────────────────────────────────────────────────────
def _generos_ctx(cancion):
    """Géneros asignados (dicts con nombreGenero/idGeneroMusical) y disponibles."""
    asignados_nombres = [g.nombre_genero for g in (getattr(cancion, 'generos', None) or [])]
    asignados = [{'nombreGenero': n, 'idGeneroMusical': n} for n in asignados_nombres]
    from types import SimpleNamespace
    disponibles = [
        SimpleNamespace(pk=n, nombre_genero=n)
        for n in catalogo_generos() if n not in asignados_nombres
    ]
    return asignados, disponibles


class AdminCancionDetailView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_cancion.html'

    def get(self, request, pk):
        cancion = get_cancion_ns(pk)
        if not cancion:
            messages.error(request, 'Canción no encontrada.')
            return redirect('catalogo:admin_cancion_list')
        asignados, _ = _generos_ctx(cancion)
        return render(request, self.template_name, {
            'cancion': cancion,
            'generos_asignados': asignados,
            'modo': 'detail',
        })


# ──────────────────────────────────────────────────────────
# UPDATE
# ──────────────────────────────────────────────────────────
class AdminCancionUpdateView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_cancion.html'

    def _ctx(self, cancion, form):
        asignados, disponibles = _generos_ctx(cancion)
        return {
            'form': form,
            'cancion': cancion,
            'generos_asignados': asignados,
            'generos_disponibles': disponibles,
            'modo': 'update',
        }

    def get(self, request, pk):
        cancion = get_cancion_ns(pk)
        if not cancion:
            return redirect('catalogo:admin_cancion_list')
        import datetime as _dt
        fecha_raw = getattr(cancion, 'fecha_lanzamiento', None)
        if isinstance(fecha_raw, (_dt.datetime,)):
            fecha_val = fecha_raw.date()
        else:
            fecha_val = fecha_raw
        form = MongoCancionAdminEditForm(initial={
            'titulo': cancion.nombre_cancion,
            'duracion': cancion.duracion,
            'numero_pista': cancion.numero_pista,
            'fecha_lanzamiento': fecha_val,
            'calidad': cancion.calidad_kbps,
            'estado': cancion.estado_cancion,
            'letra': getattr(cancion, 'letra_cancion', '') or '',
        })
        return render(request, self.template_name, self._ctx(cancion, form))

    def post(self, request, pk):
        cancion = get_cancion_ns(pk)
        if not cancion:
            return redirect('catalogo:admin_cancion_list')
        form = MongoCancionAdminEditForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, self._ctx(cancion, form))
        d = form.cleaned_data

        # Agregar género nuevo si se escribió uno
        genero_nuevo = (d.get('genero_nuevo') or '').strip()
        if genero_nuevo:
            agregar_genero_cancion(pk, genero_nuevo)

        actualizar_cancion(
            pk=pk,
            nombre=d['titulo'],
            duracion=d['duracion'],
            fecha=d.get('fecha_lanzamiento'),
            calidad=int(d['calidad']),
            numero_pista=d['numero_pista'],
            letra=d.get('letra') or '',
            estado=d['estado'],
        )
        messages.success(request, 'Canción actualizada.')
        return redirect('catalogo:admin_cancion_list')


# ──────────────────────────────────────────────────────────
# M:N embebido · Agregar / Quitar género
# ──────────────────────────────────────────────────────────
class AdminCancionGeneroAddView(RequiereAdmin, View):
    def post(self, request, pk):
        nombre = (request.POST.get('genero_id')
                  or request.POST.get('nombre_genero') or '').strip()
        if not nombre:
            messages.error(request, 'Escribe el nombre del género.')
        elif agregar_genero_cancion(pk, nombre):
            messages.success(request, f'Género "{nombre}" agregado.')
        else:
            messages.warning(request, f'El género "{nombre}" ya existe en esta canción.')
        return redirect('catalogo:admin_cancion_update', pk=pk)


class AdminCancionGeneroRemoveView(RequiereAdmin, View):
    def post(self, request, pk, nombre_genero):
        quitar_genero_cancion(pk, nombre_genero)
        messages.success(request, f'Género "{nombre_genero}" eliminado.')
        return redirect('catalogo:admin_cancion_update', pk=pk)


# ──────────────────────────────────────────────────────────
# DEACTIVATE
# ──────────────────────────────────────────────────────────
class AdminCancionDeactivateView(RequiereAdmin, View):
    def post(self, request, pk):
        cancion = get_cancion_ns(pk)
        nombre = getattr(cancion, 'nombre_cancion', pk) if cancion else pk
        desactivar_cancion(pk, artista_id=None)
        messages.success(request, f'Canción "{nombre}" desactivada.')
        return redirect('catalogo:admin_cancion_list')


# ──────────────────────────────────────────────────────────
# REPORT
# ──────────────────────────────────────────────────────────
class AdminCancionReportView(RequiereAdmin, View):
    template_name = 'catalogo/administrador/admin_cancion.html'

    def get(self, request, pk):
        cancion = get_cancion_ns(pk)
        if not cancion:
            return redirect('catalogo:admin_cancion_list')
        from ...forms.mongo_forms import AlbumReporteForm as ReporteForm
        return render(request, self.template_name, {
            'form': ReporteForm(), 'cancion': cancion, 'modo': 'report',
        })

    def post(self, request, pk):
        cancion = get_cancion_ns(pk)
        if not cancion:
            return redirect('catalogo:admin_cancion_list')
        from ...forms.mongo_forms import AlbumReporteForm as ReporteForm
        form = ReporteForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {
                'form': form, 'cancion': cancion, 'modo': 'report',
            })
        desactivar_cancion(pk, artista_id=None)
        messages.success(
            request,
            f'Canción reportada y desactivada. Motivo: {form.cleaned_data["motivo"]}'
        )
        return redirect('catalogo:admin_cancion_list')
