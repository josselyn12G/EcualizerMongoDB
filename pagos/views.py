from django.views import View
from django.shortcuts import render
from django.db import DatabaseError

from usuarios.mixins import RequiereOyente
from .services import sp_historial_suscripciones_pagos


from django.views import View
from django.shortcuts import render, redirect
from django.db import DatabaseError, connection
from django.contrib import messages

from usuarios.mixins import RequiereOyente
from .services import sp_historial_suscripciones_pagos


def _get_planes():
    try:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT idTipoPlan, nombrePlan, precio, descripcionPlan FROM Pagos.TipoPlan ORDER BY precio"
            )
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    except DatabaseError:
        return []


def _get_plan_activo(usuario_id):
    try:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT tp.idTipoPlan, tp.nombrePlan, tp.precio,
                       s.fechaInicio, s.fechaFin
                FROM Pagos.Suscripcion s
                INNER JOIN Pagos.TipoPlan tp ON tp.idTipoPlan = s.TipoPlan_idTipoPlan
                WHERE s.Usuario_idUsuario = %s
                AND s.estadoSuscripcion = 'activa'
                """,
                [usuario_id]
            )
            cols = [c[0] for c in cur.description]
            row = cur.fetchone()
            return dict(zip(cols, row)) if row else None
    except DatabaseError:
        return None


class HistorialSuscripcionesView(RequiereOyente, View):
    template_name = 'pagos/historial_suscripciones.html'

    def get(self, request):
        uid = request.session.get('usuario_id')
        try:
            historial = sp_historial_suscripciones_pagos(uid)
        except DatabaseError:
            historial = []

        plan_activo = _get_plan_activo(uid)
        planes = _get_planes()

        return render(request, self.template_name, {
            'historial':    historial,
            'total':        len(historial),
            'plan_activo':  plan_activo,
            'planes':       planes,
        })

    def post(self, request):
        uid = request.session.get('usuario_id')
        plan_id = request.POST.get('plan_id')

        if not plan_id:
            return redirect('pagos:historial')

        # Renovación automática: viene del checkbox del modal ('S' / 'N').
        # Se persiste en la columna Pagos.Suscripcion.renovacionAutomatica.
        renovacion = 'S' if request.POST.get('auto_renovacion') else 'N'

        try:
            with connection.cursor() as cur:
                # Obtener precio del plan
                cur.execute(
                    "SELECT precio FROM Pagos.TipoPlan WHERE idTipoPlan = %s",
                    [plan_id]
                )
                row = cur.fetchone()
                precio = row[0] if row else 0

                # Inactivar suscripción activa
                cur.execute(
                    """
                    UPDATE Pagos.Suscripcion
                    SET estadoSuscripcion = 'inactiva'
                    WHERE Usuario_idUsuario = %s AND estadoSuscripcion = 'activa'
                    """,
                    [uid]
                )

                # Crear nueva suscripción (guardando la renovación automática)
                cur.execute(
                    """
                    INSERT INTO Pagos.Suscripcion
                    (Usuario_idUsuario, TipoPlan_idTipoPlan, fechaInicio, fechaFin,
                     estadoSuscripcion, renovacionAutomatica)
                    VALUES (%s, %s, GETDATE(), DATEADD(month, 1, GETDATE()),
                            'activa', %s)
                    """,
                    [uid, plan_id, renovacion]
                )

                # Obtener el ID de la suscripción recién creada
                cur.execute(
                    """
                    SELECT TOP 1 idSuscripcion FROM Pagos.Suscripcion
                    WHERE Usuario_idUsuario = %s AND estadoSuscripcion = 'activa'
                    ORDER BY idSuscripcion DESC
                    """,
                    [uid]
                )
                id_suscripcion = cur.fetchone()[0]

                # Registrar pago SOLO para planes de pago (precio > 0).
                # El plan Free no genera transacción.
                if precio and float(precio) > 0:
                    cur.execute(
                        """
                        INSERT INTO Pagos.Pago
                        (Suscripcion_idSuscripcion, monto, metodoPago, fechaPago, resultadoPago)
                        VALUES (%s, %s, 'Tarjeta de credito', GETDATE(), 'Completado')
                        """,
                        [id_suscripcion, precio]
                    )
            messages.success(request, 'Tu plan se actualizó correctamente.')
        except DatabaseError:
            messages.error(request, 'No se pudo actualizar el plan. Inténtalo de nuevo.')

        return redirect('pagos:historial')