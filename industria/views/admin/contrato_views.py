"""CRUD de Contratos con Discográficas (Administrador)."""

from django.views import View
from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import DatabaseError, connection

from usuarios.mixins import RequiereAdmin
from ...models import ContratoDiscografica
from ...forms import ContratoForm


class ContratoListView(RequiereAdmin, View):
    template_name = 'industria/admin/contrato_list.html'

    def get(self, request):
        estado = request.GET.get('estado') or ''
        qs = ContratoDiscografica.objects.select_related(
            'artista', 'discografica').order_by('-fecha_inicio')
        if estado:
            qs = qs.filter(estado_contrato=estado)
        return render(request, self.template_name, {
            'contratos': qs,
            'estado_sel': estado,
            'estados': ContratoDiscografica.ESTADO_CHOICES,
        })


class ContratoCreateView(RequiereAdmin, View):
    template_name = 'industria/admin/contrato_form.html'

    def get(self, request):
        return render(request, self.template_name,
                      {'form': ContratoForm(), 'modo': 'create'})

    def post(self, request):
        form = ContratoForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Contrato creado correctamente.')
                return redirect('industria:contrato_list')
            except DatabaseError as e:
                messages.error(request, f'Error al guardar: {e}')
        return render(request, self.template_name, {'form': form, 'modo': 'create'})


# ──────────────────────────────────────────────────────────
# NOTA IMPORTANTE — Clave primaria compuesta
# La tabla [Industria].[ContratoDiscografica] tiene PK compuesta:
#   (Artista_idUsuario, Discografica_idDiscografica, idContrato)
# `idContrato` NO es único por sí solo (es un correlativo por artista
# y discográfica). Por eso identificamos cada contrato por las TRES
# columnas, y persistimos con SQL explícito para no afectar varias
# filas con el mismo idContrato.
# ──────────────────────────────────────────────────────────

def _get_contrato(artista, disco, num):
    obj = ContratoDiscografica.objects.filter(
        artista_id=artista,
        discografica_id=disco,
        id_contrato=num,
    ).first()
    if obj is None:
        raise Http404('Contrato no encontrado.')
    return obj


class ContratoUpdateView(RequiereAdmin, View):
    template_name = 'industria/admin/contrato_form.html'

    def get(self, request, artista, disco, num):
        obj = _get_contrato(artista, disco, num)
        return render(request, self.template_name,
                      {'form': ContratoForm(instance=obj), 'obj': obj, 'modo': 'update'})

    def post(self, request, artista, disco, num):
        obj = _get_contrato(artista, disco, num)
        form = ContratoForm(request.POST, instance=obj)
        if form.is_valid():
            d = form.cleaned_data
            try:
                # UPDATE explícito sobre la clave compuesta ORIGINAL para
                # garantizar que solo se modifique ESTA fila.
                with connection.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE Industria.ContratoDiscografica
                        SET Artista_idUsuario          = %s,
                            Discografica_idDiscografica = %s,
                            fechaInicio                = %s,
                            fechaFin                   = %s,
                            porcentajeArtista          = %s,
                            porcentajeDiscografica     = %s,
                            estadoContrato             = %s
                        WHERE Artista_idUsuario          = %s
                          AND Discografica_idDiscografica = %s
                          AND idContrato                 = %s
                        """,
                        [d['artista'].pk, d['discografica'].pk,
                         d['fecha_inicio'], d['fecha_fin'],
                         d['porcentaje_artista'], d['porcentaje_discografica'],
                         d['estado_contrato'],
                         artista, disco, num],
                    )
                messages.success(request, 'Contrato actualizado.')
                return redirect('industria:contrato_list')
            except DatabaseError as e:
                messages.error(request, f'Error al actualizar: {e}')
        return render(request, self.template_name,
                      {'form': form, 'obj': obj, 'modo': 'update'})


class ContratoDeleteView(RequiereAdmin, View):
    def post(self, request, artista, disco, num):
        try:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM Industria.ContratoDiscografica
                    WHERE Artista_idUsuario          = %s
                      AND Discografica_idDiscografica = %s
                      AND idContrato                 = %s
                    """,
                    [artista, disco, num],
                )
            messages.success(request, f'Contrato #{num} eliminado.')
        except DatabaseError as e:
            messages.error(request, f'No se pudo eliminar: {e}')
        return redirect('industria:contrato_list')
