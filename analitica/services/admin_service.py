"""
Wrappers Python para los SPs de Analítica del Administrador.

Cada wrapper hace EXEC del SP correspondiente y devuelve los resultados
como list[dict] (o dict único para los KPIs que devuelven una sola fila).
Es totalmente defensivo — si la conexión falla devuelve estructuras vacías
para que el dashboard siempre se renderice.
"""

from __future__ import annotations

import logging
from django.db import connection, DatabaseError


logger = logging.getLogger('ecualizer.analitica')


# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────
def _exec_rows(sql: str, params: list | None = None) -> list[dict]:
    try:
        with connection.cursor() as cur:
            cur.execute(sql, params or [])
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    except DatabaseError as e:
        logger.error('Analitica SP error · %s · %s', sql, e)
        return []


def _exec_one(sql: str, params: list | None = None) -> dict:
    rows = _exec_rows(sql, params)
    return rows[0] if rows else {}


# ──────────────────────────────────────────────────────────
# KPIs y resúmenes
# ──────────────────────────────────────────────────────────
def kpis_resumen() -> dict:
    return _exec_one("EXEC Analitica.sp_AdmKpisResumen;")


def engagement_resumen() -> dict:
    return _exec_one("EXEC Analitica.sp_AdmReproduccionesEngagement;")


def regalias_resumen() -> dict:
    return _exec_one("EXEC Analitica.sp_AdmRegaliasResumen;")


# ──────────────────────────────────────────────────────────
# Reproducciones (series y geografía)
# ──────────────────────────────────────────────────────────
def reproducciones_por_dia(dias: int = 30) -> list[dict]:
    return _exec_rows(
        "EXEC Analitica.sp_AdmReproduccionesPorDia @dias=%s;", [dias])


def reproducciones_por_hora() -> list[dict]:
    return _exec_rows("EXEC Analitica.sp_AdmReproduccionesPorHora;")


def reproducciones_por_pais(top: int = 10) -> list[dict]:
    return _exec_rows(
        "EXEC Analitica.sp_AdmReproduccionesPorPais @top=%s;", [top])


# ──────────────────────────────────────────────────────────
# Música · Géneros · Artistas · Álbumes
# ──────────────────────────────────────────────────────────
def top_generos(top: int = 10) -> list[dict]:
    return _exec_rows("EXEC Analitica.sp_AdmTopGeneros @top=%s;", [top])


def top_artistas(top: int = 10) -> list[dict]:
    return _exec_rows("EXEC Analitica.sp_AdmTopArtistas @top=%s;", [top])


def top_canciones_likes(top: int = 15) -> list[dict]:
    return _exec_rows("EXEC Analitica.sp_AdmTopCancionesLikes @top=%s;", [top])


def albumes_mas_guardados(top: int = 10) -> list[dict]:
    return _exec_rows("EXEC Analitica.sp_AdmAlbumesMasGuardados @top=%s;", [top])


def ranking_global_canciones(periodo: str = 'mes') -> list[dict]:
    """Top 20 canciones por reproducciones en el período indicado.

    Consulta directa sobre Analitica.Reproduccion (el SP
    sp_RankingGlobalCanciones puede no estar desplegado). Devuelve
    columnas: Cancion, Artista, TotalReproduccionesGlobales, OyentesUnicos.
    """
    filtros = {
        'semana': 'AND r.fechaHora >= DATEADD(DAY, -7, GETDATE())',
        'mes':    'AND r.fechaHora >= DATEADD(MONTH, -1, GETDATE())',
        'año':    'AND r.fechaHora >= DATEADD(YEAR, -1, GETDATE())',
        'anio':   'AND r.fechaHora >= DATEADD(YEAR, -1, GETDATE())',
        'todo':   '',
    }
    filtro = filtros.get(periodo, filtros['mes'])
    sql = f"""
        SELECT TOP 20
            c.nombreCancion    AS Cancion,
            ar.nombreArtistico AS Artista,
            COUNT(*)                              AS TotalReproduccionesGlobales,
            COUNT(DISTINCT r.Usuario_idUsuario)   AS OyentesUnicos
        FROM Analitica.Reproduccion r
        JOIN Catalogo.Cancion c  ON c.idCancion = r.Cancion_idCancion
        JOIN Catalogo.Album   al ON al.idAlbum  = c.Album_idAlbum
        JOIN Usuario.Artista  ar ON ar.idUsuario = al.Artista_idUsuario
        WHERE 1 = 1 {filtro}
        GROUP BY c.nombreCancion, ar.nombreArtistico
        ORDER BY TotalReproduccionesGlobales DESC;
    """
    return _exec_rows(sql)


# ──────────────────────────────────────────────────────────
# Usuarios
# ──────────────────────────────────────────────────────────
def usuarios_activos(tipo: str | None = None) -> list[dict]:
    return _exec_rows(
        "EXEC Usuario.sp_ReporteUsuariosActivos @tipoCuenta=%s;", [tipo])


def crecimiento_usuarios(meses: int = 12) -> list[dict]:
    return _exec_rows(
        "EXEC Analitica.sp_AdmCrecimientoUsuarios @meses=%s;", [meses])


def distribucion_usuarios_pais() -> list[dict]:
    return _exec_rows("EXEC Analitica.sp_AdmDistribucionUsuariosPais;")


# ──────────────────────────────────────────────────────────
# Comercial · Ingresos · Regalías
# ──────────────────────────────────────────────────────────
def ingresos_mensuales(anio: int | None = None) -> list[dict]:
    return _exec_rows(
        "EXEC Pagos.sp_ReporteIngresosMensuales @anio=%s;", [anio])


def distribucion_planes() -> list[dict]:
    return _exec_rows("EXEC Analitica.sp_AdmDistribucionPlanes;")


# ──────────────────────────────────────────────────────────
# Planes y Suscripciones (sección Comercial)
# ──────────────────────────────────────────────────────────
def listar_planes() -> list[dict]:
    return _exec_rows("EXEC Pagos.sp_AdmListarPlanes;")


def listar_suscripciones(estado: str | None = None,
                          tipo_plan_id: int | None = None) -> list[dict]:
    return _exec_rows(
        "EXEC Pagos.sp_AdmListarSuscripciones @estado=%s, @idTipoPlan=%s;",
        [estado, tipo_plan_id])


def suscripciones_kpis() -> dict:
    return _exec_one("EXEC Pagos.sp_AdmSuscripcionesKpis;")


def free_vs_premium() -> list[dict]:
    """Versión corregida que considera SOLO suscripciones vigentes."""
    return _exec_rows("EXEC Analitica.sp_AdmFreeVsPremium;")


def suscripciones_por_mes(meses: int = 12) -> list[dict]:
    return _exec_rows(
        "EXEC Pagos.sp_AdmSuscripcionesPorMes @meses=%s;", [meses])


def regalias_por_artista(top: int = 15) -> list[dict]:
    return _exec_rows(
        "EXEC Analitica.sp_AdmRegaliasPorArtista @top=%s;", [top])


def consolidado_pagos_artistas(fecha_inicio: str, fecha_fin: str) -> list[dict]:
    """Consolidado LIVE de reproducciones pendientes de facturar.

    Lee de `Analitica.Reproduccion`, excluyendo los períodos ya cerrados.
    La tarifa se fija en el SP (0.004 USD/play).
    """
    return _exec_rows(
        "EXEC Pagos.sp_ConsolidadoPagosArtistas "
        "@fechaInicio=%s, @fechaFin=%s;",
        [fecha_inicio, fecha_fin],
    )


# ──────────────────────────────────────────────────────────
# Actividad
# ──────────────────────────────────────────────────────────
def actividad_reciente(top: int = 20) -> list[dict]:
    return _exec_rows("EXEC Analitica.sp_AdmActividadReciente @top=%s;", [top])


# ──────────────────────────────────────────────────────────
# Comercial · Discográficas, Contratos, Regalías detalladas
# ──────────────────────────────────────────────────────────
def listar_discograficas(busqueda: str | None = None) -> list[dict]:
    return _exec_rows(
        "EXEC Industria.sp_AdmListarDiscograficas @busqueda=%s;", [busqueda])


def listar_contratos(estado: str | None = None) -> list[dict]:
    return _exec_rows(
        "EXEC Industria.sp_AdmListarContratos @estado=%s;", [estado])


def contratos_kpis() -> dict:
    return _exec_one("EXEC Industria.sp_AdmContratosKpis;")


def listar_regalias(desde: str | None = None,
                    hasta: str | None = None) -> list[dict]:
    return _exec_rows(
        "EXEC Analitica.sp_AdmListarRegalias @desde=%s, @hasta=%s;",
        [desde, hasta])


def regalias_por_pais() -> list[dict]:
    return _exec_rows("EXEC Analitica.sp_AdmRegaliasPorPais;")


# ──────────────────────────────────────────────────────────
# Acción · Cierre de facturación mensual (Regalías)
# ──────────────────────────────────────────────────────────
def listar_tasas_por_pais() -> list[dict]:
    """Catálogo de tarifas por país (USD/play) usado por el cierre."""
    return _exec_rows("EXEC Analitica.sp_AdmListarTasasPorPais;")


def cierre_facturacion_info() -> dict:
    """Devuelve info del último / próximo cierre de facturación mensual.

    Llaves de salida (ver SP `Analitica.sp_AdmCierreFacturacionInfo`):
      UltimoMesCerrado, UltimoAnioCerrado, UltimoPeriodoFin,
      ProximoMesACerrar, ProximoAnioACerrar, PuedeCerrarseAhora,
      ProximaFechaCierre, PendientesReproducciones.
    """
    return _exec_one("EXEC Analitica.sp_AdmCierreFacturacionInfo;")


def periodos_pendientes() -> list[dict]:
    """Devuelve los (Mes, Año) únicos de reproducciones sin cerrar."""
    return _exec_rows("EXEC Analitica.sp_AdmPeriodosPendientes;")


def cerrar_facturacion_mensual(mes: int | None = None,
                                anio: int | None = None) -> tuple[bool, str, int]:
    """
    Ejecuta `Analitica.SP_CerrarFacturacionMensual` para un período específico.
    Si `mes` o `anio` son None, el SP usa el mes anterior por defecto.

    Devuelve: (ok, mensaje, filas_insertadas).
    """
    try:
        with connection.cursor() as cur:
            cur.execute(
                "EXEC Analitica.SP_CerrarFacturacionMensual @mes=%s, @anio=%s;",
                [mes, anio],
            )
            filas = 0
            try:
                if cur.description:
                    rows = cur.fetchall()
                    filas = len(rows) if rows else 0
            except Exception:        # noqa: BLE001
                pass
        etiqueta = f' {mes}/{anio}' if mes and anio else ''
        logger.info('Cierre facturación%s OK · filas=%s', etiqueta, filas)
        msg = (f'Cierre{etiqueta} ejecutado. {filas} registro(s) procesado(s).'
               if filas else f'Cierre{etiqueta} ejecutado.')
        return True, msg, filas
    except DatabaseError as e:
        logger.error('Cierre facturación falló (%s/%s): %s', mes, anio, e)
        return False, str(e), 0


def cerrar_facturacion_todos() -> tuple[int, int, list[str]]:
    """Cierra todos los períodos pendientes.

    Devuelve: (exitosos, fallidos, errores).
    """
    pendientes = periodos_pendientes()
    exitosos, fallidos, errores = 0, 0, []
    for p in pendientes:
        ok, msg, _ = cerrar_facturacion_mensual(int(p['Mes']), int(p['Anio']))
        if ok:
            exitosos += 1
        else:
            fallidos += 1
            errores.append(f"{p['Mes']}/{p['Anio']}: {msg}")
    return exitosos, fallidos, errores
