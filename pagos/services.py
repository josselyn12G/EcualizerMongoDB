from django.db import connection


def asegurar_plan_free(usuario_id):
    """Garantiza que el oyente tenga el plan Free por defecto.

    Si el usuario NO tiene ninguna suscripción activa, crea una al plan
    Free (gratuito, sin vencimiento real y sin renovación automática).
    Devuelve True si creó la suscripción, False si ya tenía una activa
    o si no existe el plan Free.

    Es idempotente: llamarla varias veces no duplica suscripciones.
    """
    with connection.cursor() as cur:
        # ¿Ya tiene una suscripción activa? → no hacer nada.
        cur.execute(
            "SELECT 1 FROM Pagos.Suscripcion "
            "WHERE Usuario_idUsuario = %s AND estadoSuscripcion = 'activa';",
            [usuario_id],
        )
        if cur.fetchone():
            return False

        # Buscar el id del plan Free (por nombre o precio 0).
        cur.execute(
            "SELECT TOP 1 idTipoPlan FROM Pagos.TipoPlan "
            "WHERE nombrePlan = 'Free' OR precio = 0 ORDER BY precio;"
        )
        row = cur.fetchone()
        if not row:
            return False
        free_id = row[0]

        # Crear la suscripción Free: vigente, sin vencimiento práctico
        # (100 años) y sin renovación automática (es gratis).
        cur.execute(
            """
            INSERT INTO Pagos.Suscripcion
                (Usuario_idUsuario, TipoPlan_idTipoPlan,
                 fechaInicio, fechaFin, estadoSuscripcion, renovacionAutomatica)
            VALUES
                (%s, %s, CAST(GETDATE() AS DATE),
                 DATEADD(YEAR, 100, CAST(GETDATE() AS DATE)), 'activa', 'N');
            """,
            [usuario_id, free_id],
        )
        return True


def sp_historial_suscripciones_pagos(usuario_id):
    """Historial de suscripciones del oyente con sus pagos.

    Devuelve una fila por (suscripción × pago). Las suscripciones sin pago
    (p. ej. el plan Free) aparecen igualmente con los campos de pago vacíos.

    Columnas: PlanContratado, Inicio, Fin, EstadoSuscripcion,
    RenovacionAutomatica, Monto, EstadoPago, FechaPago.
    """
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT
                tp.nombrePlan          AS PlanContratado,
                s.fechaInicio          AS Inicio,
                s.fechaFin             AS Fin,
                s.estadoSuscripcion    AS EstadoSuscripcion,
                s.renovacionAutomatica AS RenovacionAutomatica,
                pg.monto               AS Monto,
                pg.resultadoPago       AS EstadoPago,
                pg.fechaPago           AS FechaPago
            FROM Pagos.Suscripcion s
            INNER JOIN Pagos.TipoPlan tp
                    ON tp.idTipoPlan = s.TipoPlan_idTipoPlan
            LEFT JOIN Pagos.Pago pg
                    ON pg.Suscripcion_idSuscripcion = s.idSuscripcion
            WHERE s.Usuario_idUsuario = %s
            ORDER BY s.idSuscripcion DESC, pg.fechaPago DESC;
            """,
            [usuario_id],
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def sp_vencer_suscripciones_expiradas():
    with connection.cursor() as cur:
        cur.execute("EXEC Pagos.SP_VencerSuscripcionesExpiradas;")
        row = cur.fetchone()
        return row[0] if row else 0


def sp_generar_recordatorios_renovacion():
    with connection.cursor() as cur:
        cur.execute("EXEC Pagos.SP_GenerarRecordatoriosRenovacion;")
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]