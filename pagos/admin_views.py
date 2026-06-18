# pagos/admin_views.py
from django.views import View
from django.shortcuts import render
from django.db import connection, DatabaseError

from usuarios.mixins import RequiereAdmin


def _fetch(sql, params=None):
    with connection.cursor() as cur:
        cur.execute(sql, params or [])
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


class AdminPlanesListView(RequiereAdmin, View):
    def get(self, request):
        try:
            planes = _fetch(
                "SELECT idTipoPlan, nombrePlan, precio, descripcionPlan, duracion "
                "FROM Pagos.TipoPlan ORDER BY idTipoPlan"
            )
        except DatabaseError:
            planes = []
        return render(request, 'pagos/admin/planes_lista.html', {
            'planes': planes,
            'total': len(planes),
        })


class AdminSuscripcionesListView(RequiereAdmin, View):
    def get(self, request):
        q = request.GET.get('q', '').strip()
        estado = request.GET.get('estado', '')
        try:
            sql = """
                SELECT
                    s.idSuscripcion,
                    p.primerNombre + ' ' + p.primerApellido AS nombreUsuario,
                    p.correo,
                    tp.nombrePlan,
                    s.fechaInicio,
                    s.fechaFin,
                    s.estadoSuscripcion
                FROM Pagos.Suscripcion s
                INNER JOIN Usuario.Persona p ON p.idUsuario = s.Usuario_idUsuario
                INNER JOIN Pagos.TipoPlan tp ON tp.idTipoPlan = s.TipoPlan_idTipoPlan
                WHERE 1=1
            """
            params = []
            if q:
                sql += " AND (p.primerNombre LIKE %s OR p.primerApellido LIKE %s OR p.correo LIKE %s)"
                params += [f'%{q}%', f'%{q}%', f'%{q}%']
            if estado:
                sql += " AND s.estadoSuscripcion = %s"
                params.append(estado)
            sql += " ORDER BY s.idSuscripcion DESC"
            suscripciones = _fetch(sql, params)
        except DatabaseError:
            suscripciones = []
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
        try:
            sql = """
                SELECT
                    pg.idPago,
                    p.primerNombre + ' ' + p.primerApellido AS nombreUsuario,
                    p.correo,
                    tp.nombrePlan,
                    pg.monto,
                    pg.metodoPago,
                    pg.fechaPago,
                    pg.resultadoPago
                FROM Pagos.Pago pg
                INNER JOIN Pagos.Suscripcion s ON s.idSuscripcion = pg.Suscripcion_idSuscripcion
                INNER JOIN Usuario.Persona p ON p.idUsuario = s.Usuario_idUsuario
                INNER JOIN Pagos.TipoPlan tp ON tp.idTipoPlan = s.TipoPlan_idTipoPlan
                WHERE 1=1
            """
            params = []
            if q:
                sql += " AND (p.primerNombre LIKE %s OR p.correo LIKE %s)"
                params += [f'%{q}%', f'%{q}%']
            if resultado:
                sql += " AND pg.resultadoPago = %s"
                params.append(resultado)
            sql += " ORDER BY pg.idPago DESC"
            pagos = _fetch(sql, params)
        except DatabaseError:
            pagos = []
        return render(request, 'pagos/admin/pagos_lista.html', {
            'pagos': pagos,
            'total': len(pagos),
            'q': q,
            'resultado_sel': resultado,
        })
        
class AdminIngresosView(RequiereAdmin, View):
    def get(self, request):
        anio = request.GET.get('anio', '2024')
        try:
            ingresos = _fetch(
                "EXEC Pagos.sp_ReporteIngresosMensuales @anio=%s;",
                [anio]
            )
        except DatabaseError:
            ingresos = []

        total = sum(float(r.get('TotalIngresos') or 0) for r in ingresos)

        return render(request, 'pagos/admin/ingresos_lista.html', {
            'ingresos': ingresos,
            'total': total,
            'anio': anio,
        })

