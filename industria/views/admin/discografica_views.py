"""CRUD de Discográficas (Administrador) — MongoDB."""

from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages

from usuarios.mixins import RequiereAdmin
from ...forms import DiscograficaForm
from ... import mongo_service as ms


class DiscograficaListView(RequiereAdmin, View):
    template_name = 'industria/admin/discografica_list.html'

    def get(self, request):
        q = (request.GET.get('q') or '').strip()
        return render(request, self.template_name, {
            'discograficas': ms.listar_discograficas(busqueda=q or None),
            'q': q,
        })


class DiscograficaCreateView(RequiereAdmin, View):
    template_name = 'industria/admin/discografica_form.html'

    def get(self, request):
        return render(request, self.template_name,
                      {'form': DiscograficaForm(), 'modo': 'create'})

    def post(self, request):
        form = DiscograficaForm(request.POST)
        if form.is_valid():
            d = form.cleaned_data
            ms.crear_discografica(d['nombre_discografica'], d['pais_origen'],
                                  d['correo_contacto'], d['telefono_contacto'])
            messages.success(request, 'Discográfica creada correctamente.')
            return redirect('industria:discografica_list')
        return render(request, self.template_name, {'form': form, 'modo': 'create'})


class DiscograficaUpdateView(RequiereAdmin, View):
    template_name = 'industria/admin/discografica_form.html'

    def get(self, request, pk):
        obj = ms.get_discografica(pk)
        if not obj:
            messages.error(request, 'Discográfica no encontrada.')
            return redirect('industria:discografica_list')
        form = DiscograficaForm(initial={
            'nombre_discografica': obj.nombre_discografica,
            'pais_origen': obj.pais_origen,
            'correo_contacto': obj.correo_contacto,
            'telefono_contacto': obj.telefono_contacto,
        }, exclude_pk=pk)
        return render(request, self.template_name,
                      {'form': form, 'obj': obj, 'modo': 'update'})

    def post(self, request, pk):
        obj = ms.get_discografica(pk)
        if not obj:
            messages.error(request, 'Discográfica no encontrada.')
            return redirect('industria:discografica_list')
        form = DiscograficaForm(request.POST, exclude_pk=pk)
        if form.is_valid():
            d = form.cleaned_data
            ms.actualizar_discografica(pk, d['nombre_discografica'], d['pais_origen'],
                                       d['correo_contacto'], d['telefono_contacto'])
            messages.success(request, 'Discográfica actualizada.')
            return redirect('industria:discografica_list')
        return render(request, self.template_name,
                      {'form': form, 'obj': obj, 'modo': 'update'})


class DiscograficaDeleteView(RequiereAdmin, View):
    def post(self, request, pk):
        ok, msg = ms.eliminar_discografica(pk)
        if ok:
            messages.success(request, f'Discográfica "{msg}" eliminada.')
        else:
            messages.error(request, msg)
        return redirect('industria:discografica_list')
