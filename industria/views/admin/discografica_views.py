"""CRUD de Discográficas (Administrador)."""

from django.views import View
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse
from django.db import DatabaseError

from usuarios.mixins import RequiereAdmin
from ...models import Discografica
from ...forms import DiscograficaForm


class DiscograficaListView(RequiereAdmin, View):
    template_name = 'industria/admin/discografica_list.html'

    def get(self, request):
        q = (request.GET.get('q') or '').strip()
        qs = Discografica.objects.all().order_by('nombre_discografica')
        if q:
            qs = qs.filter(nombre_discografica__icontains=q)
        return render(request, self.template_name, {'discograficas': qs, 'q': q})


class DiscograficaCreateView(RequiereAdmin, View):
    template_name = 'industria/admin/discografica_form.html'

    def get(self, request):
        return render(request, self.template_name,
                      {'form': DiscograficaForm(), 'modo': 'create'})

    def post(self, request):
        form = DiscograficaForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Discográfica creada correctamente.')
                return redirect('industria:discografica_list')
            except DatabaseError as e:
                messages.error(request, f'Error al guardar: {e}')
        return render(request, self.template_name, {'form': form, 'modo': 'create'})


class DiscograficaUpdateView(RequiereAdmin, View):
    template_name = 'industria/admin/discografica_form.html'

    def get(self, request, pk):
        obj = get_object_or_404(Discografica, pk=pk)
        return render(request, self.template_name,
                      {'form': DiscograficaForm(instance=obj), 'obj': obj, 'modo': 'update'})

    def post(self, request, pk):
        obj = get_object_or_404(Discografica, pk=pk)
        form = DiscograficaForm(request.POST, instance=obj)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Discográfica actualizada.')
                return redirect('industria:discografica_list')
            except DatabaseError as e:
                messages.error(request, f'Error al actualizar: {e}')
        return render(request, self.template_name,
                      {'form': form, 'obj': obj, 'modo': 'update'})


class DiscograficaDeleteView(RequiereAdmin, View):
    def post(self, request, pk):
        obj = get_object_or_404(Discografica, pk=pk)
        try:
            obj.delete()
            messages.success(request, f'Discográfica "{obj.nombre_discografica}" eliminada.')
        except DatabaseError as e:
            messages.error(request, f'No se pudo eliminar (revisa contratos asociados): {e}')
        return redirect('industria:discografica_list')
