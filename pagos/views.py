"""Vistas del oyente para el módulo de pagos (datos desde MongoDB)."""
from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages

from usuarios.mixins import RequiereOyente
from . import mongo_service as svc


class HistorialSuscripcionesView(RequiereOyente, View):
    template_name = 'pagos/historial_suscripciones.html'

    def get(self, request):
        uid = request.session.get('usuario_id')
        # Garantiza el plan Free por defecto si el oyente no tiene suscripción.
        svc.asegurar_plan_free(uid)

        historial = svc.historial_oyente(uid)
        return render(request, self.template_name, {
            'historial':   historial,
            'total':       len(historial),
            'plan_activo': svc.plan_activo_oyente(uid),
            'planes':      svc.listar_planes(),
        })

    def post(self, request):
        # Solo cambios a plan GRATUITO llegan aquí (los de paga pasan por la
        # pantalla de pago simulado). La renovación llega como checkbox.
        uid = request.session.get('usuario_id')
        plan_id = request.POST.get('plan_id')
        if not plan_id:
            return redirect('pagos:historial')
        renovacion = bool(request.POST.get('auto_renovacion'))
        if svc.cambiar_plan_oyente(uid, plan_id, renovacion):
            messages.success(request, 'Tu plan se actualizó correctamente.')
        else:
            messages.error(request, 'No se pudo actualizar el plan. Inténtalo de nuevo.')
        return redirect('pagos:historial')


class PagoSuscripcionView(RequiereOyente, View):
    """Pantalla de pago SIMULADO para planes de paga. Recoge método de pago
    (Tarjeta de crédito / débito / Paypal) y datos de tarjeta (no se guardan),
    y al confirmar realiza el cobro simulado y activa la suscripción."""
    template_name = 'pagos/pago_simulado.html'

    def get(self, request, plan_id):
        plan = svc.admin_get_plan(plan_id)
        if not plan or not plan.get('precio'):
            # Plan inexistente o gratuito → no requiere pago.
            return redirect('pagos:historial')
        return render(request, self.template_name, {'plan': plan})

    def post(self, request, plan_id):
        plan = svc.admin_get_plan(plan_id)
        if not plan or not plan.get('precio'):
            return redirect('pagos:historial')
        metodo = request.POST.get('metodo_pago', 'Tarjeta de credito')
        renovacion = bool(request.POST.get('auto_renovacion'))
        if svc.cambiar_plan_oyente(request.session.get('usuario_id'), plan_id, renovacion, metodo):
            messages.success(
                request,
                f'¡Pago realizado con éxito! Ahora tienes el plan {plan["nombrePlan"]}.')
        else:
            messages.error(request, 'No se pudo procesar el pago. Inténtalo de nuevo.')
        return redirect('pagos:historial')
