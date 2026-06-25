"""CRUD de Contratos con Discográficas (Administrador) — MongoDB.

En Mongo cada contrato tiene un `contratoId` único, así que se identifica por
un solo `pk` (ObjectId), a diferencia del modelo SQL con clave compuesta.
"""

from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages

from usuarios.mixins import RequiereAdmin
from ...forms import ContratoForm
from ... import mongo_service as ms

ESTADOS = [(e, e) for e in ms.ESTADOS_CONTRATO]


class ContratoListView(RequiereAdmin, View):
    template_name = 'industria/admin/contrato_list.html'

    def get(self, request):
        estado = request.GET.get('estado') or ''
        return render(request, self.template_name, {
            'contratos': ms.listar_contratos(estado=estado or None),
            'estado_sel': estado,
            'estados': ESTADOS,
        })


class ContratoCreateView(RequiereAdmin, View):
    template_name = 'industria/admin/contrato_form.html'

    def get(self, request):
        return render(request, self.template_name,
                      {'form': ContratoForm(), 'modo': 'create'})

    def post(self, request):
        form = ContratoForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            ms.crear_contrato(
                artista_id=d['artista'], discografica_id=d['discografica'],
                fecha_inicio=d['fecha_inicio'], fecha_fin=d.get('fecha_fin'),
                pct_artista=d['porcentaje_artista'],
                pct_disco=d['porcentaje_discografica'],
                estado=d['estado_contrato'])
            messages.success(request, 'Contrato creado correctamente.')
            return redirect('industria:contrato_list')
        return render(request, self.template_name, {'form': form, 'modo': 'create'})


class ContratoUpdateView(RequiereAdmin, View):
    template_name = 'industria/admin/contrato_form.html'

    def get(self, request, pk):
        obj = ms.get_contrato(pk)
        if not obj:
            messages.error(request, 'Contrato no encontrado.')
            return redirect('industria:contrato_list')
        form = ContratoForm(initial={
            'artista': obj.artista_id,
            'discografica': obj.discografica_id,
            'fecha_inicio': obj.fecha_inicio,
            'fecha_fin': obj.fecha_fin,
            'porcentaje_artista': obj.porcentaje_artista,
            'porcentaje_discografica': obj.porcentaje_discografica,
            'estado_contrato': obj.estado_contrato,
        })
        return render(request, self.template_name,
                      {'form': form, 'obj': obj, 'modo': 'update'})

    def post(self, request, pk):
        obj = ms.get_contrato(pk)
        if not obj:
            messages.error(request, 'Contrato no encontrado.')
            return redirect('industria:contrato_list')
        form = ContratoForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            ms.actualizar_contrato(
                pk, artista_id=d['artista'], discografica_id=d['discografica'],
                fecha_inicio=d['fecha_inicio'], fecha_fin=d.get('fecha_fin'),
                pct_artista=d['porcentaje_artista'],
                pct_disco=d['porcentaje_discografica'],
                estado=d['estado_contrato'])
            messages.success(request, 'Contrato actualizado.')
            return redirect('industria:contrato_list')
        return render(request, self.template_name,
                      {'form': form, 'obj': obj, 'modo': 'update'})


class ContratoDeleteView(RequiereAdmin, View):
    def post(self, request, pk):
        if ms.eliminar_contrato(pk):
            messages.success(request, 'Contrato eliminado.')
        else:
            messages.error(request, 'No se pudo eliminar el contrato.')
        return redirect('industria:contrato_list')
