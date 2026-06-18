from django.views import View
from django.shortcuts import render
from django.db import connection, DatabaseError

from usuarios.mixins import RequiereArtista


def _fetch(sql, params=None):
    with connection.cursor() as cur:
        cur.execute(sql, params or [])
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


class ArtistaMonetizacionView(RequiereArtista, View):
    template_name = 'pagos/artista/monetizacion.html'

    def get(self, request):
        uid = request.session.get('usuario_id')
        fecha_inicio = request.GET.get('fecha_inicio', '').strip()
        fecha_fin = request.GET.get('fecha_fin', '').strip()

        regalias = []
        error = None

        if fecha_inicio and fecha_fin:
            try:
                with connection.cursor() as cur:
                    cur.execute(
                        "EXEC Pagos.sp_ReporteRegaliasArtista "
                        "@idArtista=%s, @fechaInicio=%s, @fechaFin=%s;",
                        [uid, fecha_inicio, fecha_fin]
                    )
                    cols = [c[0] for c in cur.description]
                    regalias = [dict(zip(cols, row)) for row in cur.fetchall()]
            except DatabaseError as e:
                error = str(e)

        total_monto = sum(float(r.get('MontoNetoArtista') or 0) for r in regalias)

        return render(request, self.template_name, {
            'regalias':     regalias,
            'total':        len(regalias),
            'total_monto':  total_monto,
            'fecha_inicio': fecha_inicio,
            'fecha_fin':    fecha_fin,
            'error':        error,
        })