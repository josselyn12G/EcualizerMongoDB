# pagos/admin_views.py — Panel admin del módulo de pagos (datos desde MongoDB)
from django.views import View
from django.shortcuts import render, redirect
from django.http import Http404
from django.contrib import messages

from usuarios.mixins import RequiereAdmin
from .forms import PlanForm
from . import mongo_service as svc


class AdminPlanesListView(RequiereAdmin, View):
    def get(self, request):
        planes = svc.listar_planes()
        return render(request, 'pagos/admin/planes_lista.html', {
            'planes': planes,
            'total': len(planes),
        })


class AdminPlanCrearView(RequiereAdmin, View):
    template_name = 'pagos/admin/plan_form.html'

    def get(self, request):
        return render(request, self.template_name, {'form': PlanForm(), 'modo': 'crear'})

    def post(self, request):
        form = PlanForm(request.POST)
        if form.is_valid():
            svc.crear_plan(form.cleaned_data)
            messages.success(request, 'Plan creado correctamente.')
            return redirect('admin_planes_list')
        return render(request, self.template_name, {'form': form, 'modo': 'crear'})


class AdminPlanEditarView(RequiereAdmin, View):
    template_name = 'pagos/admin/plan_form.html'

    def get(self, request, pk):
        plan = svc.admin_get_plan(pk)
        if not plan:
            raise Http404('Plan no encontrado')
        form = PlanForm(initial={
            'nombre_plan': plan['nombrePlan'],
            'precio': plan['precio'],
            'duracion': plan['duracion'],
            'descripcion': plan['descripcionPlan'],
        })
        return render(request, self.template_name, {'form': form, 'modo': 'editar', 'plan': plan})

    def post(self, request, pk):
        plan = svc.admin_get_plan(pk)
        if not plan:
            raise Http404('Plan no encontrado')
        form = PlanForm(request.POST)
        if form.is_valid():
            svc.actualizar_plan(pk, form.cleaned_data)
            messages.success(request, 'Plan actualizado. Los nuevos precios aplican a futuras compras.')
            return redirect('admin_planes_list')
        return render(request, self.template_name, {'form': form, 'modo': 'editar', 'plan': plan})


class AdminSuscripcionesListView(RequiereAdmin, View):
    def get(self, request):
        q = request.GET.get('q', '').strip()
        estado = request.GET.get('estado', '')
        suscripciones = svc.admin_listar_suscripciones(q, estado)
        return render(request, 'pagos/admin/suscripciones_lista.html', {
            'suscripciones': suscripciones,
            'total': len(suscripciones),
            'q': q,
            'estado_sel': estado,
        })


class AdminPagosListView(RequiereAdmin, View):
    def get(self, request):
        q = request.GET.get('q', '').strip()
        resultado = request.GET.get('resultado', '')
        pagos = svc.admin_listar_pagos(q, resultado)
        return render(request, 'pagos/admin/pagos_lista.html', {
            'pagos': pagos,
            'total': len(pagos),
            'q': q,
            'resultado_sel': resultado,
        })


class AdminIngresosView(RequiereAdmin, View):
    def get(self, request):
        anio = request.GET.get('anio') or str(svc.ultimo_anio_con_pagos())
        ingresos = svc.admin_ingresos_mensuales(anio)
        total = sum(float(r['TotalIngresos']) for r in ingresos)
        return render(request, 'pagos/admin/ingresos_lista.html', {
            'ingresos': ingresos,
            'total': total,
            'anio': anio,
        })
