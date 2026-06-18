-- ====================================================================
--          ANALÍTICA DEL ADMINISTRADOR · BLOQUE EXTENDIDO
-- ====================================================================
-- Procedimientos agregados para alimentar el Dashboard de Analítica del
-- administrador. Convención de nombres: sp_Adm<Categoria><Detalle>.
-- Todos devuelven SELECT (sin OUT params) → fáciles de consumir desde
-- Django con cursor.execute() + fetchall().
--
-- Permisos: RolAdministrador + RolReportes.
-- ====================================================================


-- -------------------------------------------------------------------
--  sp_AdmKpisResumen — KPIs principales del sistema (4-8 tarjetas)
-- -------------------------------------------------------------------
CREATE OR ALTER PROCEDURE Analitica.sp_AdmKpisResumen
AS
BEGIN
    SET NOCOUNT ON;
    -- Una suscripción se considera VIGENTE si su estado es 'activa' y su
    -- fechaFin no ha pasado todavía (cubre planes cancelados antes de su fin).
    -- Los pagos "exitosos" en el DDL usan resultadoPago = 'Completado'.
    SELECT
        (SELECT COUNT(*) FROM Usuario.Usuario)                              AS TotalOyentes,
        (SELECT COUNT(*) FROM Usuario.Artista)                              AS TotalArtistas,
        (SELECT COUNT(*) FROM Catalogo.Cancion WHERE estadoCancion='activa') AS TotalCanciones,
        (SELECT COUNT(*) FROM Catalogo.Album   WHERE estadoAlbum='activo')   AS TotalAlbumes,
        (SELECT COUNT(*) FROM Analitica.Reproduccion)                       AS TotalReproducciones,
        (SELECT ISNULL(SUM(monto),0) FROM Pagos.Pago WHERE resultadoPago='Completado') AS IngresosTotales,
        (SELECT COUNT(*) FROM Pagos.Suscripcion
            WHERE estadoSuscripcion='activa' AND fechaFin >= GETDATE())      AS SuscripcionesActivas,
        (SELECT COUNT(*) FROM Biblioteca.UsuarioCancionLike)                AS TotalLikes;
END
GO
GRANT EXECUTE ON Analitica.sp_AdmKpisResumen TO RolAdministrador;
GRANT EXECUTE ON Analitica.sp_AdmKpisResumen TO RolReportes;
GO


-- -------------------------------------------------------------------
--  sp_AdmReproduccionesPorDia — line chart, últimos N días
-- -------------------------------------------------------------------
CREATE OR ALTER PROCEDURE Analitica.sp_AdmReproduccionesPorDia
    @dias INT = 30
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        CAST(fechaHora AS DATE)             AS Fecha,
        COUNT(*)                            AS Reproducciones,
        COUNT(DISTINCT Usuario_idUsuario)   AS OyentesUnicos
    FROM Analitica.Reproduccion
    WHERE fechaHora >= DATEADD(DAY, -@dias, GETDATE())
    GROUP BY CAST(fechaHora AS DATE)
    ORDER BY Fecha ASC;
END
GO
GRANT EXECUTE ON Analitica.sp_AdmReproduccionesPorDia TO RolAdministrador;
GRANT EXECUTE ON Analitica.sp_AdmReproduccionesPorDia TO RolReportes;
GO


-- -------------------------------------------------------------------
--  sp_AdmReproduccionesPorHora — patrones horarios 0..23
-- -------------------------------------------------------------------
CREATE OR ALTER PROCEDURE Analitica.sp_AdmReproduccionesPorHora
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        DATEPART(HOUR, fechaHora) AS Hora,
        COUNT(*)                  AS Reproducciones
    FROM Analitica.Reproduccion
    WHERE fechaHora >= DATEADD(DAY, -30, GETDATE())
    GROUP BY DATEPART(HOUR, fechaHora)
    ORDER BY Hora;
END
GO
GRANT EXECUTE ON Analitica.sp_AdmReproduccionesPorHora TO RolAdministrador;
GRANT EXECUTE ON Analitica.sp_AdmReproduccionesPorHora TO RolReportes;
GO


-- -------------------------------------------------------------------
--  sp_AdmReproduccionesPorPais — distribución geográfica (pie)
-- -------------------------------------------------------------------
CREATE OR ALTER PROCEDURE Analitica.sp_AdmReproduccionesPorPais
    @top INT = 10
AS
BEGIN
    SET NOCOUNT ON;
    SELECT TOP (@top)
        ISNULL(pais, 'Desconocido')         AS Pais,
        COUNT(*)                            AS Reproducciones,
        COUNT(DISTINCT Usuario_idUsuario)   AS OyentesUnicos
    FROM Analitica.Reproduccion
    GROUP BY pais
    ORDER BY Reproducciones DESC;
END
GO
GRANT EXECUTE ON Analitica.sp_AdmReproduccionesPorPais TO RolAdministrador;
GRANT EXECUTE ON Analitica.sp_AdmReproduccionesPorPais TO RolReportes;
GO


-- -------------------------------------------------------------------
--  sp_AdmReproduccionesEngagement — tasa de skip + duración promedio
-- -------------------------------------------------------------------
CREATE OR ALTER PROCEDURE Analitica.sp_AdmReproduccionesEngagement
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        COUNT(*)                                       AS TotalReproducciones,
        AVG(CAST(duracionEscuchada AS DECIMAL(10,2))) AS DuracionPromedioSeg,
        SUM(CASE WHEN fueSaltada='S' THEN 1 ELSE 0 END) AS TotalSaltadas,
        CAST(
            (SUM(CASE WHEN fueSaltada='S' THEN 1.0 ELSE 0 END) * 100) /
            NULLIF(COUNT(*), 0)
        AS DECIMAL(5,2))                              AS PorcentajeSkipRate,
        COUNT(DISTINCT Usuario_idUsuario)             AS OyentesUnicos,
        COUNT(DISTINCT Cancion_idCancion)             AS CancionesUnicas
    FROM Analitica.Reproduccion
    WHERE fechaHora >= DATEADD(DAY, -30, GETDATE());
END
GO
GRANT EXECUTE ON Analitica.sp_AdmReproduccionesEngagement TO RolAdministrador;
GRANT EXECUTE ON Analitica.sp_AdmReproduccionesEngagement TO RolReportes;
GO


-- -------------------------------------------------------------------
--  sp_AdmTopGeneros — bar chart de géneros más reproducidos
-- -------------------------------------------------------------------
CREATE OR ALTER PROCEDURE Analitica.sp_AdmTopGeneros
    @top INT = 10
AS
BEGIN
    SET NOCOUNT ON;
    SELECT TOP (@top)
        GM.nombreGenero                  AS Genero,
        COUNT(R.idReproduccion)          AS Reproducciones,
        COUNT(DISTINCT C.idCancion)      AS Canciones
    FROM Catalogo.GeneroMusical GM
    INNER JOIN Catalogo.CancionGeneroMusical CGM
            ON GM.idGeneroMusical = CGM.GeneroMusical_idGeneroMusical
    INNER JOIN Catalogo.Cancion C ON CGM.Cancion_idCancion = C.idCancion
    LEFT  JOIN Analitica.Reproduccion R ON R.Cancion_idCancion = C.idCancion
    GROUP BY GM.nombreGenero
    ORDER BY Reproducciones DESC;
END
GO
GRANT EXECUTE ON Analitica.sp_AdmTopGeneros TO RolAdministrador;
GRANT EXECUTE ON Analitica.sp_AdmTopGeneros TO RolReportes;
GO


-- -------------------------------------------------------------------
--  sp_AdmTopArtistas — artistas más reproducidos
-- -------------------------------------------------------------------
CREATE OR ALTER PROCEDURE Analitica.sp_AdmTopArtistas
    @top INT = 10
AS
BEGIN
    SET NOCOUNT ON;
    SELECT TOP (@top)
        Art.idUsuario                       AS idArtista,
        Art.nombreArtistico                 AS Artista,
        COUNT(R.idReproduccion)             AS Reproducciones,
        COUNT(DISTINCT R.Usuario_idUsuario) AS OyentesUnicos,
        (SELECT COUNT(*) FROM Catalogo.Album
          WHERE Artista_idUsuario = Art.idUsuario AND estadoAlbum='activo') AS TotalAlbumes
    FROM Usuario.Artista Art
    LEFT JOIN Catalogo.Album Alb ON Alb.Artista_idUsuario = Art.idUsuario
    LEFT JOIN Catalogo.Cancion C ON C.Album_idAlbum = Alb.idAlbum
    LEFT JOIN Analitica.Reproduccion R ON R.Cancion_idCancion = C.idCancion
    GROUP BY Art.idUsuario, Art.nombreArtistico
    ORDER BY Reproducciones DESC;
END
GO
GRANT EXECUTE ON Analitica.sp_AdmTopArtistas TO RolAdministrador;
GRANT EXECUTE ON Analitica.sp_AdmTopArtistas TO RolReportes;
GO


-- -------------------------------------------------------------------
--  sp_AdmAlbumesMasGuardados — Biblioteca.UsuarioAlbum
-- -------------------------------------------------------------------
CREATE OR ALTER PROCEDURE Analitica.sp_AdmAlbumesMasGuardados
    @top INT = 10
AS
BEGIN
    SET NOCOUNT ON;
    SELECT TOP (@top)
        Alb.idAlbum,
        Alb.tituloAlbum             AS Album,
        Art.nombreArtistico         AS Artista,
        COUNT(UA.Usuario_idUsuario) AS VecesGuardado
    FROM Catalogo.Album Alb
    INNER JOIN Usuario.Artista Art ON Art.idUsuario = Alb.Artista_idUsuario
    LEFT  JOIN Biblioteca.UsuarioAlbum UA ON UA.Album_idAlbum = Alb.idAlbum
    WHERE Alb.estadoAlbum = 'activo'
    GROUP BY Alb.idAlbum, Alb.tituloAlbum, Art.nombreArtistico
    ORDER BY VecesGuardado DESC;
END
GO
GRANT EXECUTE ON Analitica.sp_AdmAlbumesMasGuardados TO RolAdministrador;
GRANT EXECUTE ON Analitica.sp_AdmAlbumesMasGuardados TO RolReportes;
GO


-- -------------------------------------------------------------------
--  sp_AdmTopCancionesLikes — canciones con más likes
-- -------------------------------------------------------------------
CREATE OR ALTER PROCEDURE Analitica.sp_AdmTopCancionesLikes
    @top INT = 15
AS
BEGIN
    SET NOCOUNT ON;
    SELECT TOP (@top)
        C.idCancion,
        C.nombreCancion              AS Cancion,
        Art.nombreArtistico          AS Artista,
        Alb.tituloAlbum              AS Album,
        COUNT(UCL.Usuario_idUsuario) AS TotalLikes,
        C.totalReproducciones        AS Reproducciones
    FROM Catalogo.Cancion C
    INNER JOIN Catalogo.Album Alb   ON Alb.idAlbum = C.Album_idAlbum
    INNER JOIN Usuario.Artista Art  ON Art.idUsuario = Alb.Artista_idUsuario
    LEFT  JOIN Biblioteca.UsuarioCancionLike UCL ON UCL.Cancion_idCancion = C.idCancion
    WHERE C.estadoCancion = 'activa'
    GROUP BY C.idCancion, C.nombreCancion, Art.nombreArtistico, Alb.tituloAlbum, C.totalReproducciones
    ORDER BY TotalLikes DESC;
END
GO
GRANT EXECUTE ON Analitica.sp_AdmTopCancionesLikes TO RolAdministrador;
GRANT EXECUTE ON Analitica.sp_AdmTopCancionesLikes TO RolReportes;
GO


-- -------------------------------------------------------------------
--  sp_AdmCrecimientoUsuarios — nuevos oyentes por mes
-- -------------------------------------------------------------------
CREATE OR ALTER PROCEDURE Analitica.sp_AdmCrecimientoUsuarios
    @meses INT = 12
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        FORMAT(P.fechaRegistro, 'yyyy-MM') AS Mes,
        COUNT(*) AS NuevosUsuarios
    FROM Usuario.Persona P
    WHERE P.fechaRegistro >= DATEADD(MONTH, -@meses, GETDATE())
    GROUP BY FORMAT(P.fechaRegistro, 'yyyy-MM')
    ORDER BY Mes;
END
GO
GRANT EXECUTE ON Analitica.sp_AdmCrecimientoUsuarios TO RolAdministrador;
GRANT EXECUTE ON Analitica.sp_AdmCrecimientoUsuarios TO RolReportes;
GO


-- -------------------------------------------------------------------
--  sp_AdmDistribucionUsuariosPais — pie chart oyentes por país
-- -------------------------------------------------------------------
CREATE OR ALTER PROCEDURE Analitica.sp_AdmDistribucionUsuariosPais
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        paisUsuario AS Pais,
        COUNT(*)    AS Oyentes
    FROM Usuario.Usuario
    GROUP BY paisUsuario
    ORDER BY Oyentes DESC;
END
GO
GRANT EXECUTE ON Analitica.sp_AdmDistribucionUsuariosPais TO RolAdministrador;
GRANT EXECUTE ON Analitica.sp_AdmDistribucionUsuariosPais TO RolReportes;
GO


-- -------------------------------------------------------------------
--  sp_AdmRegaliasResumen — snapshot total de regalías
-- -------------------------------------------------------------------
CREATE OR ALTER PROCEDURE Analitica.sp_AdmRegaliasResumen
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        COUNT(*)                              AS TotalRegistros,
        ISNULL(SUM(montoTotalGenerado),0)    AS MontoTotalGenerado,
        ISNULL(SUM(cantidadReproducciones),0) AS ReproduccionesTotales,
        ISNULL(AVG(montoTotalGenerado),0)    AS MontoPromedio
    FROM Analitica.Regalia;
END
GO
GRANT EXECUTE ON Analitica.sp_AdmRegaliasResumen TO RolAdministrador;
GRANT EXECUTE ON Analitica.sp_AdmRegaliasResumen TO RolReportes;
GO


-- -------------------------------------------------------------------
--  sp_AdmRegaliasPorArtista — ranking de regalías por artista
-- -------------------------------------------------------------------
CREATE OR ALTER PROCEDURE Analitica.sp_AdmRegaliasPorArtista
    @top INT = 15
AS
BEGIN
    SET NOCOUNT ON;
    SELECT TOP (@top)
        Art.idUsuario          AS idArtista,
        Art.nombreArtistico    AS Artista,
        COUNT(R.idRegalia)     AS PagosRegistrados,
        ISNULL(SUM(R.cantidadReproducciones),0) AS ReproduccionesTotales,
        ISNULL(SUM(R.montoTotalGenerado),0)    AS MontoTotalGenerado
    FROM Usuario.Artista Art
    LEFT JOIN Catalogo.Album Alb ON Alb.Artista_idUsuario = Art.idUsuario
    LEFT JOIN Catalogo.Cancion C ON C.Album_idAlbum = Alb.idAlbum
    LEFT JOIN Analitica.Regalia R ON R.Cancion_idCancion = C.idCancion
    GROUP BY Art.idUsuario, Art.nombreArtistico
    ORDER BY MontoTotalGenerado DESC;
END
GO
GRANT EXECUTE ON Analitica.sp_AdmRegaliasPorArtista TO RolAdministrador;
GRANT EXECUTE ON Analitica.sp_AdmRegaliasPorArtista TO RolReportes;
GO


-- -------------------------------------------------------------------
--  sp_AdmActividadReciente — feed mezclado de eventos
-- -------------------------------------------------------------------
CREATE OR ALTER PROCEDURE Analitica.sp_AdmActividadReciente
    @top INT = 20
AS
BEGIN
    SET NOCOUNT ON;
    SELECT TOP (@top) * FROM (
        SELECT 'reproduccion' AS Tipo, R.fechaHora AS Fecha,
               U.alias        AS Quien,
               C.nombreCancion AS Que,
               R.pais          AS Detalle
        FROM Analitica.Reproduccion R
        INNER JOIN Usuario.Usuario U ON U.idUsuario = R.Usuario_idUsuario
        INNER JOIN Catalogo.Cancion C ON C.idCancion = R.Cancion_idCancion
        UNION ALL
        SELECT 'like' AS Tipo, UCL.fechaLike,
               U.alias, C.nombreCancion, NULL
        FROM Biblioteca.UsuarioCancionLike UCL
        INNER JOIN Usuario.Usuario U ON U.idUsuario = UCL.Usuario_idUsuario
        INNER JOIN Catalogo.Cancion C ON C.idCancion = UCL.Cancion_idCancion
        UNION ALL
        SELECT 'seguir' AS Tipo, CAST(USA.fechaSeguimiento AS DATETIME),
               U.alias, Art.nombreArtistico, NULL
        FROM Biblioteca.UsuarioSigueArtista USA
        INNER JOIN Usuario.Usuario U   ON U.idUsuario  = USA.Usuario_idUsuario
        INNER JOIN Usuario.Artista Art ON Art.idUsuario = USA.Artista_idUsuario
    ) AS act
    ORDER BY Fecha DESC;
END
GO
GRANT EXECUTE ON Analitica.sp_AdmActividadReciente TO RolAdministrador;
GRANT EXECUTE ON Analitica.sp_AdmActividadReciente TO RolReportes;
GO


-- -------------------------------------------------------------------
--  sp_AdmDistribucionPlanes — pie chart de planes activos
-- -------------------------------------------------------------------
CREATE OR ALTER PROCEDURE Analitica.sp_AdmDistribucionPlanes
AS
BEGIN
    SET NOCOUNT ON;
    -- Distribución de oyentes por plan EFECTIVO HOY:
    --   - Se cuenta cada TipoPlan con sus suscripciones VIGENTES
    --     (estado='activa' AND fechaFin >= hoy).
    --   - "Plan" es palabra reservada → alias [Plan].
    SELECT
        TP.nombrePlan AS [Plan],
        COUNT(S.idSuscripcion) AS Suscriptores,
        TP.precio     AS Precio,
        TP.duracion   AS Duracion
    FROM Pagos.TipoPlan TP
    LEFT JOIN Pagos.Suscripcion S
        ON S.TipoPlan_idTipoPlan = TP.idTipoPlan
        AND S.estadoSuscripcion  = 'activa'
        AND S.fechaFin          >= GETDATE()
    GROUP BY TP.nombrePlan, TP.precio, TP.duracion
    ORDER BY Suscriptores DESC, TP.nombrePlan;
END
GO
GRANT EXECUTE ON Analitica.sp_AdmDistribucionPlanes TO RolAdministrador;
GRANT EXECUTE ON Analitica.sp_AdmDistribucionPlanes TO RolReportes;
GO


-- ====================================================================
--          COMERCIAL · Discográficas · Contratos · Regalías
-- ====================================================================

-- sp_AdmListarDiscograficas
CREATE OR ALTER PROCEDURE Industria.sp_AdmListarDiscograficas
    @busqueda VARCHAR(150) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        D.idDiscografica,
        D.nombreDiscografica,
        D.paisOrigen,
        D.correoContacto,
        D.telefonoContacto,
        (SELECT COUNT(*) FROM Industria.ContratoDiscografica CD
         WHERE CD.Discografica_idDiscografica = D.idDiscografica) AS TotalContratos,
        (SELECT COUNT(*) FROM Industria.ContratoDiscografica CD
         WHERE CD.Discografica_idDiscografica = D.idDiscografica
           AND CD.estadoContrato = 'Activo') AS ContratosActivos
    FROM Industria.Discografica D
    WHERE (@busqueda IS NULL OR D.nombreDiscografica LIKE '%' + @busqueda + '%')
    ORDER BY D.nombreDiscografica;
END
GO
GRANT EXECUTE ON Industria.sp_AdmListarDiscograficas TO RolAdministrador;
GRANT EXECUTE ON Industria.sp_AdmListarDiscograficas TO RolReportes;
GO


-- sp_AdmListarContratos
CREATE OR ALTER PROCEDURE Industria.sp_AdmListarContratos
    @estado VARCHAR(20) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        CD.idContrato,
        CD.fechaInicio,
        CD.fechaFin,
        CD.porcentajeArtista,
        CD.porcentajeDiscografica,
        CD.estadoContrato,
        Art.idUsuario        AS idArtista,
        Art.nombreArtistico  AS Artista,
        D.idDiscografica,
        D.nombreDiscografica AS Discografica
    FROM Industria.ContratoDiscografica CD
    INNER JOIN Usuario.Artista     Art ON Art.idUsuario      = CD.Artista_idUsuario
    INNER JOIN Industria.Discografica D ON D.idDiscografica  = CD.Discografica_idDiscografica
    WHERE (@estado IS NULL OR CD.estadoContrato = @estado)
    ORDER BY CD.fechaInicio DESC;
END
GO
GRANT EXECUTE ON Industria.sp_AdmListarContratos TO RolAdministrador;
GRANT EXECUTE ON Industria.sp_AdmListarContratos TO RolReportes;
GO


-- sp_AdmContratosKpis
CREATE OR ALTER PROCEDURE Industria.sp_AdmContratosKpis
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        COUNT(*)                                                AS TotalContratos,
        SUM(CASE WHEN estadoContrato='Activo'     THEN 1 ELSE 0 END) AS Activos,
        SUM(CASE WHEN estadoContrato='Cancelado'  THEN 1 ELSE 0 END) AS Cancelados,
        SUM(CASE WHEN estadoContrato='Finalizado' THEN 1 ELSE 0 END) AS Finalizados,
        (SELECT COUNT(*) FROM Industria.Discografica)           AS TotalDiscograficas,
        (SELECT COUNT(DISTINCT Artista_idUsuario)
         FROM Industria.ContratoDiscografica
         WHERE estadoContrato='Activo')                         AS ArtistasContratados
    FROM Industria.ContratoDiscografica;
END
GO
GRANT EXECUTE ON Industria.sp_AdmContratosKpis TO RolAdministrador;
GRANT EXECUTE ON Industria.sp_AdmContratosKpis TO RolReportes;
GO


-- sp_AdmListarRegalias (registros guardados en Analitica.Regalia)
-- Nota: la tabla Regalia almacena el periodo como (mesPeriodo, anioPeriodo).
-- Calculamos las fechas de inicio/fin del mes en SQL para entregarlas al template.
CREATE OR ALTER PROCEDURE Analitica.sp_AdmListarRegalias
    @desde DATE = NULL,
    @hasta DATE = NULL
AS
BEGIN
    SET NOCOUNT ON;
    ;WITH RegaliasFechas AS (
        SELECT
            R.idRegalia,
            R.cantidadReproducciones,
            R.montoTotalGenerado,
            R.paisReproduccion,
            R.mesPeriodo,
            R.anioPeriodo,
            R.Cancion_idCancion,
            DATEFROMPARTS(R.anioPeriodo, R.mesPeriodo, 1)        AS fechaInicioPeriodo,
            EOMONTH(DATEFROMPARTS(R.anioPeriodo, R.mesPeriodo, 1)) AS fechaFinPeriodo
        FROM Analitica.Regalia R
    )
    SELECT
        RF.idRegalia,
        RF.cantidadReproducciones,
        RF.montoTotalGenerado,
        RF.fechaInicioPeriodo,
        RF.fechaFinPeriodo,
        RF.paisReproduccion,
        C.idCancion,
        C.nombreCancion       AS Cancion,
        Alb.tituloAlbum       AS Album,
        Art.idUsuario         AS idArtista,
        Art.nombreArtistico   AS Artista
    FROM RegaliasFechas RF
    INNER JOIN Catalogo.Cancion C   ON C.idCancion  = RF.Cancion_idCancion
    INNER JOIN Catalogo.Album   Alb ON Alb.idAlbum  = C.Album_idAlbum
    INNER JOIN Usuario.Artista  Art ON Art.idUsuario = Alb.Artista_idUsuario
    WHERE (@desde IS NULL OR RF.fechaInicioPeriodo >= @desde)
      AND (@hasta IS NULL OR RF.fechaFinPeriodo    <= @hasta)
    ORDER BY RF.fechaFinPeriodo DESC, RF.montoTotalGenerado DESC;
END
GO
GRANT EXECUTE ON Analitica.sp_AdmListarRegalias TO RolAdministrador;
GRANT EXECUTE ON Analitica.sp_AdmListarRegalias TO RolReportes;
GO


-- sp_AdmRegaliasPorPais
CREATE OR ALTER PROCEDURE Analitica.sp_AdmRegaliasPorPais
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        ISNULL(paisReproduccion,'Desconocido') AS Pais,
        COUNT(*)                                AS Registros,
        ISNULL(SUM(cantidadReproducciones),0)  AS Reproducciones,
        ISNULL(SUM(montoTotalGenerado),0)      AS MontoTotal
    FROM Analitica.Regalia
    GROUP BY paisReproduccion
    ORDER BY MontoTotal DESC;
END
GO
GRANT EXECUTE ON Analitica.sp_AdmRegaliasPorPais TO RolAdministrador;
GRANT EXECUTE ON Analitica.sp_AdmRegaliasPorPais TO RolReportes;
GO


-- ====================================================================
--          SUSCRIPCIONES · pieza nueva
-- ====================================================================
-- "Plan" del usuario = TipoPlan asociado mediante Pagos.Suscripcion.
-- Estos SPs alimentan la sección Comercial → Planes y Suscripciones.


-- sp_AdmListarPlanes — catálogo completo de TipoPlan con métricas
CREATE OR ALTER PROCEDURE Pagos.sp_AdmListarPlanes
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        TP.idTipoPlan,
        TP.nombrePlan,
        TP.descripcionPlan,
        TP.precio,
        TP.duracion,
        ISNULL((SELECT COUNT(*) FROM Pagos.Suscripcion S
                WHERE S.TipoPlan_idTipoPlan = TP.idTipoPlan), 0)              AS TotalSuscripciones,
        ISNULL((SELECT COUNT(*) FROM Pagos.Suscripcion S
                WHERE S.TipoPlan_idTipoPlan = TP.idTipoPlan
                  AND S.estadoSuscripcion = 'activa'
                  AND S.fechaFin >= GETDATE()), 0)                            AS SuscripcionesActivas,
        ISNULL((SELECT SUM(P.monto) FROM Pagos.Pago P
                INNER JOIN Pagos.Suscripcion S ON S.idSuscripcion = P.Suscripcion_idSuscripcion
                WHERE S.TipoPlan_idTipoPlan = TP.idTipoPlan
                  AND P.resultadoPago = 'Completado'), 0)                     AS IngresosGenerados
    FROM Pagos.TipoPlan TP
    ORDER BY TP.precio DESC, TP.nombrePlan;
END
GO
GRANT EXECUTE ON Pagos.sp_AdmListarPlanes TO RolAdministrador;
GRANT EXECUTE ON Pagos.sp_AdmListarPlanes TO RolReportes;
GO


-- sp_AdmListarSuscripciones — listado con usuario + plan
CREATE OR ALTER PROCEDURE Pagos.sp_AdmListarSuscripciones
    @estado VARCHAR(20) = NULL,
    @idTipoPlan SMALLINT = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        S.idSuscripcion,
        S.fechaInicio,
        S.fechaFin,
        S.estadoSuscripcion,
        S.renovacionAutomatica,
        CASE
            WHEN S.estadoSuscripcion = 'activa' AND S.fechaFin >= GETDATE() THEN 'Vigente'
            WHEN S.estadoSuscripcion = 'activa' AND S.fechaFin <  GETDATE() THEN 'Vencida'
            ELSE S.estadoSuscripcion
        END                                       AS EstadoEfectivo,
        U.idUsuario                               AS idUsuario,
        U.alias                                   AS Alias,
        P.primerNombre + ' ' + P.primerApellido   AS Usuario,
        P.correo                                  AS Correo,
        TP.idTipoPlan,
        TP.nombrePlan                             AS [Plan],
        TP.precio                                 AS Precio,
        TP.duracion                               AS Duracion
    FROM Pagos.Suscripcion S
    INNER JOIN Pagos.TipoPlan       TP ON TP.idTipoPlan = S.TipoPlan_idTipoPlan
    INNER JOIN Usuario.Usuario      U  ON U.idUsuario  = S.Usuario_idUsuario
    INNER JOIN Usuario.Persona      P  ON P.idUsuario  = U.idUsuario
    WHERE (@estado     IS NULL OR S.estadoSuscripcion    = @estado)
      AND (@idTipoPlan IS NULL OR S.TipoPlan_idTipoPlan = @idTipoPlan)
    ORDER BY S.fechaInicio DESC;
END
GO
GRANT EXECUTE ON Pagos.sp_AdmListarSuscripciones TO RolAdministrador;
GRANT EXECUTE ON Pagos.sp_AdmListarSuscripciones TO RolReportes;
GO


-- sp_AdmSuscripcionesKpis — tarjetas para el panel de suscripciones
CREATE OR ALTER PROCEDURE Pagos.sp_AdmSuscripcionesKpis
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        (SELECT COUNT(*) FROM Pagos.Suscripcion)                                      AS TotalHistorico,
        (SELECT COUNT(*) FROM Pagos.Suscripcion
            WHERE estadoSuscripcion='activa' AND fechaFin >= GETDATE())               AS Vigentes,
        (SELECT COUNT(*) FROM Pagos.Suscripcion
            WHERE estadoSuscripcion='activa' AND fechaFin <  GETDATE())               AS Vencidas,
        (SELECT COUNT(*) FROM Pagos.Suscripcion WHERE estadoSuscripcion='cancelada')  AS Canceladas,
        (SELECT COUNT(*) FROM Pagos.Suscripcion WHERE estadoSuscripcion='inactiva')   AS Inactivas,
        (SELECT COUNT(*) FROM Pagos.Suscripcion
            WHERE renovacionAutomatica='S'
              AND estadoSuscripcion='activa' AND fechaFin >= GETDATE())               AS ConRenovacionAutomatica,
        (SELECT COUNT(DISTINCT Usuario_idUsuario) FROM Pagos.Suscripcion
            WHERE estadoSuscripcion='activa' AND fechaFin >= GETDATE())               AS UsuariosConPlanVigente;
END
GO
GRANT EXECUTE ON Pagos.sp_AdmSuscripcionesKpis TO RolAdministrador;
GRANT EXECUTE ON Pagos.sp_AdmSuscripcionesKpis TO RolReportes;
GO


-- sp_AdmFreeVsPremium — segmenta oyentes en Free vs Premium
-- (versión corregida del sp_ReporteUsuariosActivos: ahora solo cuenta como
--  Premium si la suscripción está VIGENTE — activa y dentro de fecha).
CREATE OR ALTER PROCEDURE Analitica.sp_AdmFreeVsPremium
AS
BEGIN
    SET NOCOUNT ON;
    ;WITH PlanVigente AS (
        -- Para cada usuario, el plan vigente (si tiene)
        SELECT
            U.idUsuario,
            (SELECT TOP 1 TP.nombrePlan
               FROM Pagos.Suscripcion S
               INNER JOIN Pagos.TipoPlan TP ON TP.idTipoPlan = S.TipoPlan_idTipoPlan
               WHERE S.Usuario_idUsuario   = U.idUsuario
                 AND S.estadoSuscripcion   = 'activa'
                 AND S.fechaFin           >= GETDATE()
               ORDER BY S.fechaInicio DESC) AS NombrePlan
        FROM Usuario.Usuario U
    )
    SELECT
        CASE
            WHEN NombrePlan IS NULL OR NombrePlan LIKE '%Free%' THEN 'Free'
            ELSE 'Premium'
        END                              AS TipoCuentaActual,
        COUNT(*)                         AS CantidadUsuarios,
        CAST(COUNT(*) * 100.0 /
             NULLIF(SUM(COUNT(*)) OVER(), 0) AS DECIMAL(5,2)) AS Porcentaje
    FROM PlanVigente
    GROUP BY CASE
                WHEN NombrePlan IS NULL OR NombrePlan LIKE '%Free%' THEN 'Free'
                ELSE 'Premium'
             END
    ORDER BY CantidadUsuarios DESC;
END
GO
GRANT EXECUTE ON Analitica.sp_AdmFreeVsPremium TO RolAdministrador;
GRANT EXECUTE ON Analitica.sp_AdmFreeVsPremium TO RolReportes;
GO


-- sp_AdmSuscripcionesPorMes — series mensuales (nuevas / canceladas)
CREATE OR ALTER PROCEDURE Pagos.sp_AdmSuscripcionesPorMes
    @meses INT = 12
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        FORMAT(S.fechaInicio, 'yyyy-MM')                                  AS Mes,
        COUNT(*)                                                          AS NuevasSuscripciones,
        SUM(CASE WHEN S.estadoSuscripcion = 'cancelada' THEN 1 ELSE 0 END) AS Canceladas
    FROM Pagos.Suscripcion S
    WHERE S.fechaInicio >= DATEADD(MONTH, -@meses, GETDATE())
    GROUP BY FORMAT(S.fechaInicio, 'yyyy-MM')
    ORDER BY Mes;
END
GO
GRANT EXECUTE ON Pagos.sp_AdmSuscripcionesPorMes TO RolAdministrador;
GRANT EXECUTE ON Pagos.sp_AdmSuscripcionesPorMes TO RolReportes;
GO

-- =====================================================================
--  CONSOLIDADO DE PAGOS A ARTISTAS · VISTA EN VIVO (PRE-CIERRE)
-- ---------------------------------------------------------------------
--  Lee directamente de `Analitica.Reproduccion` (no de Regalia).
--  Agrupa por artista + discográfica + período (mes/año) y calcula
--  cuánto se debe pagar usando una tarifa fija (0.004 USD/play),
--  aplicando los porcentajes del contrato activo si existe.
--
--  EXCLUYE los períodos que YA fueron cerrados (existen en Regalia) —
--  así esta tabla muestra únicamente reproducciones PENDIENTES de
--  facturar. Apenas se reproduce una canción aparece aquí; apenas se
--  ejecuta el cierre mensual deja de aparecer (queda en el histórico).
--
--  El parámetro @valorPorReproduccion queda por compatibilidad pero
--  se ignora; siempre usamos 0.004 (la misma tarifa del SP de cierre).
-- =====================================================================
CREATE OR ALTER PROCEDURE Pagos.sp_ConsolidadoPagosArtistas
    @fechaInicio DATE,
    @fechaFin DATE,
    @valorPorReproduccion DECIMAL(10,4) = 0.0040
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @tarifa DECIMAL(12,6) = 0.004;

    SELECT
        Art.nombreArtistico                                  AS BeneficiarioArtista,
        ISNULL(D.nombreDiscografica, 'Independiente')        AS Discografica,
        YEAR(R.fechaHora)                                    AS AnioPeriodo,
        MONTH(R.fechaHora)                                   AS MesPeriodo,
        DATEFROMPARTS(YEAR(R.fechaHora), MONTH(R.fechaHora), 1)        AS FechaInicioPeriodo,
        EOMONTH(DATEFROMPARTS(YEAR(R.fechaHora), MONTH(R.fechaHora),1))AS FechaFinPeriodo,
        COUNT(*)                                             AS TotalReproduccionesPeriodo,
        CAST(COUNT(*) * @tarifa AS DECIMAL(18,2))            AS MontoBrutoTotal,
        CAST(COUNT(*) * @tarifa
             * (ISNULL(CD.porcentajeDiscografica, 0) / 100.0)
             AS DECIMAL(18,2))                               AS PagoADiscografica,
        CAST(COUNT(*) * @tarifa
             * (ISNULL(CD.porcentajeArtista, 100) / 100.0)
             AS DECIMAL(18,2))                               AS PagoNetoArtista
    FROM Analitica.Reproduccion R
    INNER JOIN Catalogo.Cancion C    ON C.idCancion = R.Cancion_idCancion
    INNER JOIN Catalogo.Album   Alb  ON Alb.idAlbum = C.Album_idAlbum
    INNER JOIN Usuario.Artista  Art  ON Art.idUsuario = Alb.Artista_idUsuario
    LEFT JOIN Industria.ContratoDiscografica CD
           ON CD.Artista_idUsuario = Art.idUsuario
          AND CD.estadoContrato    = 'Activo'
          AND CD.fechaInicio      <= CAST(R.fechaHora AS DATE)
          AND (CD.fechaFin IS NULL
               OR CD.fechaFin     >= CAST(R.fechaHora AS DATE))
    LEFT JOIN Industria.Discografica D
           ON D.idDiscografica = CD.Discografica_idDiscografica
    WHERE CAST(R.fechaHora AS DATE) BETWEEN @fechaInicio AND @fechaFin
      -- Excluye períodos ya cerrados (existen en Analitica.Regalia)
      AND NOT EXISTS (
            SELECT 1 FROM Analitica.Regalia Reg
             WHERE Reg.mesPeriodo  = MONTH(R.fechaHora)
               AND Reg.anioPeriodo = YEAR(R.fechaHora)
          )
    GROUP BY
        Art.nombreArtistico,
        D.nombreDiscografica,
        YEAR(R.fechaHora),
        MONTH(R.fechaHora),
        CD.porcentajeArtista,
        CD.porcentajeDiscografica
    ORDER BY AnioPeriodo DESC, MesPeriodo DESC, PagoNetoArtista DESC;
END
GO
GRANT EXECUTE ON Pagos.sp_ConsolidadoPagosArtistas TO RolAdministrador;
GRANT EXECUTE ON Pagos.sp_ConsolidadoPagosArtistas TO RolReportes;
GO


-- =====================================================================
--  INFO DEL CIERRE DE FACTURACIÓN · ÚLTIMO / PRÓXIMO
-- ---------------------------------------------------------------------
--  Devuelve una fila con:
--   - UltimoMesCerrado, UltimoAnioCerrado    (NULL si nunca se cerró)
--   - UltimoPeriodoFin  (último día del último período cerrado)
--   - ProximoMesACerrar, ProximoAnioACerrar  (mes anterior al actual)
--   - PuedeCerrarseAhora (1 si el mes anterior aún no está en Regalia)
--   - ProximaFechaCierre (cuándo se podrá ejecutar el próximo cierre)
--   - PendientesReproducciones (cuántas reproducciones esperan cierre)
-- =====================================================================
CREATE OR ALTER PROCEDURE Analitica.sp_AdmCierreFacturacionInfo
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @mesAnterior  TINYINT  = MONTH(DATEADD(MONTH, -1, GETDATE()));
    DECLARE @anioAnterior SMALLINT = YEAR(DATEADD(MONTH, -1, GETDATE()));

    DECLARE @ultMes  TINYINT, @ultAnio SMALLINT;
    SELECT TOP 1
        @ultMes  = mesPeriodo,
        @ultAnio = anioPeriodo
    FROM Analitica.Regalia
    ORDER BY anioPeriodo DESC, mesPeriodo DESC;

    DECLARE @puedeCerrarseAhora BIT = 0;
    IF NOT EXISTS (
        SELECT 1 FROM Analitica.Regalia
         WHERE mesPeriodo = @mesAnterior
           AND anioPeriodo = @anioAnterior
    )
        SET @puedeCerrarseAhora = 1;

    -- Si el mes anterior ya está cerrado, el siguiente cierre será el
    -- 1er día del mes que viene (sobre el mes actual completado).
    DECLARE @proximaFecha DATE;
    IF @puedeCerrarseAhora = 1
        SET @proximaFecha = CAST(GETDATE() AS DATE);
    ELSE
        SET @proximaFecha = DATEFROMPARTS(
            YEAR(DATEADD(MONTH, 1, GETDATE())),
            MONTH(DATEADD(MONTH, 1, GETDATE())),
            1);

    DECLARE @pendientes BIGINT;
    SELECT @pendientes = COUNT(*)
    FROM Analitica.Reproduccion R
    WHERE NOT EXISTS (
        SELECT 1 FROM Analitica.Regalia Reg
         WHERE Reg.mesPeriodo  = MONTH(R.fechaHora)
           AND Reg.anioPeriodo = YEAR(R.fechaHora)
    );

    SELECT
        @ultMes                                      AS UltimoMesCerrado,
        @ultAnio                                     AS UltimoAnioCerrado,
        CASE WHEN @ultMes IS NULL THEN NULL
             ELSE EOMONTH(DATEFROMPARTS(@ultAnio, @ultMes, 1))
        END                                          AS UltimoPeriodoFin,
        @mesAnterior                                 AS ProximoMesACerrar,
        @anioAnterior                                AS ProximoAnioACerrar,
        @puedeCerrarseAhora                          AS PuedeCerrarseAhora,
        @proximaFecha                                AS ProximaFechaCierre,
        ISNULL(@pendientes, 0)                       AS PendientesReproducciones;
END
GO
GRANT EXECUTE ON Analitica.sp_AdmCierreFacturacionInfo TO RolAdministrador;
GRANT EXECUTE ON Analitica.sp_AdmCierreFacturacionInfo TO RolReportes;
GO


-- =====================================================================
--  CATÁLOGO DE TARIFAS POR PAÍS · Analitica.TasaPorPais
-- ---------------------------------------------------------------------
--  Cada reproducción genera un monto distinto según el país desde el
--  cual se realizó. Esta tabla actúa como catálogo maestro: el SP de
--  cierre y la vista de consolidado leen la tarifa de aquí.
--  Si el país no figura, se usa una tarifa base (0.004 USD/play).
-- =====================================================================
IF OBJECT_ID('Analitica.TasaPorPais','U') IS NULL
BEGIN
    CREATE TABLE Analitica.TasaPorPais (
        pais   VARCHAR(60)   NOT NULL,
        tarifa DECIMAL(12,6) NOT NULL,
        CONSTRAINT TasaPorPais_PK PRIMARY KEY CLUSTERED (pais),
        CONSTRAINT CHK_TasaPorPais_tarifa CHECK (tarifa >= 0)
    );
END
GO

-- Seed / upsert del catálogo. Vuelve a ejecutarse seguro (MERGE).
MERGE Analitica.TasaPorPais AS dst
USING (VALUES
    ('Estados Unidos', 0.005000),
    ('Reino Unido',    0.004800),
    ('España',         0.004500),
    ('Alemania',       0.004500),
    ('Francia',        0.004500),
    ('México',         0.004000),
    ('Brasil',         0.004000),
    ('Argentina',      0.003500),
    ('Chile',          0.003500),
    ('Uruguay',        0.003500),
    ('Colombia',       0.003200),
    ('Perú',           0.003000),
    ('Ecuador',        0.003000),
    ('Venezuela',      0.002800),
    ('Bolivia',        0.002800),
    ('Paraguay',       0.002800)
) AS src(pais, tarifa)
   ON dst.pais = src.pais
WHEN MATCHED AND dst.tarifa <> src.tarifa THEN UPDATE SET tarifa = src.tarifa
WHEN NOT MATCHED BY TARGET THEN
    INSERT (pais, tarifa) VALUES (src.pais, src.tarifa);
GO


-- =====================================================================
--  FUNCIÓN ESCALAR · Tarifa por país con fallback
-- ---------------------------------------------------------------------
--  Devuelve la tarifa configurada para @pais; si no existe registro
--  cae a la tarifa base (0.004 USD/play).
-- =====================================================================
CREATE OR ALTER FUNCTION Analitica.fn_TasaPorPais(@pais VARCHAR(60))
RETURNS DECIMAL(12,6)
AS
BEGIN
    RETURN ISNULL(
        (SELECT tarifa FROM Analitica.TasaPorPais WHERE pais = @pais),
        0.004
    );
END
GO


-- =====================================================================
--  LISTAR CATÁLOGO DE TARIFAS POR PAÍS (para mostrar en UI)
-- =====================================================================
CREATE OR ALTER PROCEDURE Analitica.sp_AdmListarTasasPorPais
AS
BEGIN
    SET NOCOUNT ON;
    SELECT pais AS Pais, tarifa AS Tarifa
    FROM Analitica.TasaPorPais
    ORDER BY tarifa DESC, pais;
END
GO
GRANT EXECUTE ON Analitica.sp_AdmListarTasasPorPais TO RolAdministrador;
GRANT EXECUTE ON Analitica.sp_AdmListarTasasPorPais TO RolReportes;
GO


-- =====================================================================
--  REEMPLAZO DE sp_ConsolidadoPagosArtistas · CON PAÍS Y TARIFA POR PAÍS
-- ---------------------------------------------------------------------
--  Agrupa por artista + discográfica + período + PAÍS, multiplicando
--  por la tarifa específica del país (Analitica.fn_TasaPorPais).
-- =====================================================================
CREATE OR ALTER PROCEDURE Pagos.sp_ConsolidadoPagosArtistas
    @fechaInicio DATE,
    @fechaFin DATE,
    @valorPorReproduccion DECIMAL(10,4) = NULL  -- ignorado; tarifa por país
AS
BEGIN
    SET NOCOUNT ON;

    ;WITH RepEnRango AS (
        SELECT
            R.idReproduccion,
            R.Cancion_idCancion,
            R.pais,
            R.fechaHora,
            ISNULL(TP.tarifa, 0.004) AS tarifaPais
        FROM Analitica.Reproduccion R
        LEFT JOIN Analitica.TasaPorPais TP
               ON TP.pais = R.pais
        WHERE CAST(R.fechaHora AS DATE) BETWEEN @fechaInicio AND @fechaFin
          AND NOT EXISTS (
                SELECT 1 FROM Analitica.Regalia Reg
                 WHERE Reg.mesPeriodo  = MONTH(R.fechaHora)
                   AND Reg.anioPeriodo = YEAR(R.fechaHora)
              )
    )
    SELECT
        Art.nombreArtistico                                       AS BeneficiarioArtista,
        ISNULL(D.nombreDiscografica, 'Independiente')             AS Discografica,
        ISNULL(R.pais, 'Desconocido')                             AS Pais,
        R.tarifaPais                                              AS TarifaPais,
        YEAR(R.fechaHora)                                         AS AnioPeriodo,
        MONTH(R.fechaHora)                                        AS MesPeriodo,
        DATEFROMPARTS(YEAR(R.fechaHora), MONTH(R.fechaHora),1)    AS FechaInicioPeriodo,
        EOMONTH(DATEFROMPARTS(YEAR(R.fechaHora),MONTH(R.fechaHora),1)) AS FechaFinPeriodo,
        COUNT(*)                                                  AS TotalReproduccionesPeriodo,
        CAST(SUM(R.tarifaPais) AS DECIMAL(18,2))                  AS MontoBrutoTotal,
        CAST(SUM(R.tarifaPais
                 * (ISNULL(CD.porcentajeDiscografica, 0) / 100.0))
             AS DECIMAL(18,2))                                    AS PagoADiscografica,
        CAST(SUM(R.tarifaPais
                 * (ISNULL(CD.porcentajeArtista, 100) / 100.0))
             AS DECIMAL(18,2))                                    AS PagoNetoArtista
    FROM RepEnRango R
    INNER JOIN Catalogo.Cancion C    ON C.idCancion = R.Cancion_idCancion
    INNER JOIN Catalogo.Album   Alb  ON Alb.idAlbum = C.Album_idAlbum
    INNER JOIN Usuario.Artista  Art  ON Art.idUsuario = Alb.Artista_idUsuario
    LEFT JOIN Industria.ContratoDiscografica CD
           ON CD.Artista_idUsuario = Art.idUsuario
          AND CD.estadoContrato    = 'Activo'
          AND CD.fechaInicio      <= CAST(R.fechaHora AS DATE)
          AND (CD.fechaFin IS NULL
               OR CD.fechaFin     >= CAST(R.fechaHora AS DATE))
    LEFT JOIN Industria.Discografica D
           ON D.idDiscografica = CD.Discografica_idDiscografica
    GROUP BY
        Art.nombreArtistico,
        D.nombreDiscografica,
        R.pais,
        R.tarifaPais,
        YEAR(R.fechaHora),
        MONTH(R.fechaHora),
        CD.porcentajeArtista,
        CD.porcentajeDiscografica
    ORDER BY AnioPeriodo DESC, MesPeriodo DESC, BeneficiarioArtista, Pais;
END
GO
GRANT EXECUTE ON Pagos.sp_ConsolidadoPagosArtistas TO RolAdministrador;
GRANT EXECUTE ON Pagos.sp_ConsolidadoPagosArtistas TO RolReportes;
GO


-- =====================================================================
--  ACTUALIZACIÓN DEL CIERRE MENSUAL · TARIFA POR PAÍS
-- ---------------------------------------------------------------------
--  Reemplaza Analitica.SP_CerrarFacturacionMensual para que use la
--  tabla Analitica.TasaPorPais en lugar de una tarifa fija.
-- =====================================================================
CREATE OR ALTER PROCEDURE Analitica.SP_CerrarFacturacionMensual
    @mes  TINYINT  = NULL,
    @anio SMALLINT = NULL
AS
BEGIN
    SET NOCOUNT ON;

    -- Si no se especifica período, usa el mes anterior (comportamiento legacy).
    DECLARE @mesPeriodo  TINYINT  = ISNULL(@mes,  MONTH(DATEADD(MONTH, -1, GETDATE())));
    DECLARE @anioPeriodo SMALLINT = ISNULL(@anio, YEAR(DATEADD(MONTH, -1, GETDATE())));

    BEGIN TRY
        BEGIN TRANSACTION;

        IF EXISTS (
            SELECT 1 FROM Analitica.Regalia
             WHERE mesPeriodo  = @mesPeriodo
               AND anioPeriodo = @anioPeriodo
        )
        BEGIN
            RAISERROR('Ya existen registros de regalía para el período %d/%d. El cierre no puede ejecutarse dos veces.',
                      16, 1, @mesPeriodo, @anioPeriodo);
            ROLLBACK TRANSACTION;
            RETURN;
        END

        ;WITH RepDelPeriodo AS (
            SELECT
                R.Cancion_idCancion,
                R.pais,
                ISNULL(TP.tarifa, 0.004) AS tarifaPais,
                AL.Artista_idUsuario
            FROM Analitica.Reproduccion R
            INNER JOIN Catalogo.Cancion C  ON C.idCancion = R.Cancion_idCancion
            INNER JOIN Catalogo.Album   AL ON AL.idAlbum  = C.Album_idAlbum
            LEFT JOIN  Analitica.TasaPorPais TP ON TP.pais = R.pais
            WHERE MONTH(R.fechaHora) = @mesPeriodo
              AND YEAR(R.fechaHora)  = @anioPeriodo
        )
        INSERT INTO Analitica.Regalia
            (Cancion_idCancion, cantidadReproducciones, montoTotalGenerado,
             montoArtista, montoDiscografica, paisReproduccion,
             mesPeriodo, anioPeriodo)
        SELECT
            X.Cancion_idCancion,
            COUNT(*)                                          AS cantidadReproducciones,
            CAST(SUM(X.tarifaPais) AS DECIMAL(12,2))          AS montoTotalGenerado,
            CAST(SUM(X.tarifaPais
                     * (ISNULL(CD.porcentajeArtista,100)/100.0))
                 AS DECIMAL(12,2))                            AS montoArtista,
            CAST(SUM(X.tarifaPais
                     * (ISNULL(CD.porcentajeDiscografica,0)/100.0))
                 AS DECIMAL(12,2))                            AS montoDiscografica,
            X.pais                                            AS paisReproduccion,
            @mesPeriodo,
            @anioPeriodo
        FROM RepDelPeriodo X
        LEFT JOIN Industria.ContratoDiscografica CD
               ON CD.Artista_idUsuario = X.Artista_idUsuario
              AND CD.estadoContrato    = 'Activo'
              AND CD.fechaInicio      <= EOMONTH(DATEFROMPARTS(@anioPeriodo, @mesPeriodo, 1))
              AND (CD.fechaFin IS NULL
                   OR CD.fechaFin     >= DATEFROMPARTS(@anioPeriodo, @mesPeriodo, 1))
        GROUP BY
            X.Cancion_idCancion,
            X.pais,
            CD.porcentajeArtista,
            CD.porcentajeDiscografica;

        COMMIT TRANSACTION;

        SELECT
            @mesPeriodo                  AS MesProcesado,
            @anioPeriodo                 AS AnioProcesado,
            COUNT(*)                     AS TotalRegistros,
            SUM(cantidadReproducciones)  AS TotalReproducciones,
            SUM(montoTotalGenerado)      AS MontoTotalGenerado,
            SUM(montoArtista)            AS MontoTotalArtistas,
            SUM(montoDiscografica)       AS MontoTotalDiscograficas
        FROM Analitica.Regalia
        WHERE mesPeriodo  = @mesPeriodo
          AND anioPeriodo = @anioPeriodo;

    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END
GO
GRANT EXECUTE ON Analitica.SP_CerrarFacturacionMensual TO RolAdministrador;
GO


-- =====================================================================
--  PERÍODOS PENDIENTES DE CIERRE
-- ---------------------------------------------------------------------
--  Devuelve los (mes, año) únicos de reproducciones que aún no han
--  sido cerradas. Usado por el botón "Ejecutar todos".
-- =====================================================================
-- =====================================================================
--  GRANTs faltantes para el SP existente de regalías del artista
--  (en el script original no se aplicaron — esto causa "permission denied").
-- =====================================================================
GRANT EXECUTE ON Pagos.sp_ReporteRegaliasArtista TO RolSistema;
GRANT EXECUTE ON Pagos.sp_ReporteRegaliasArtista TO RolArtista;
GRANT EXECUTE ON Pagos.sp_ReporteRegaliasArtista TO RolAdministrador;
GRANT EXECUTE ON Pagos.sp_ReporteRegaliasArtista TO RolReportes;
GO


-- =====================================================================
--  HISTORIAL DE REGALÍAS DE UN ARTISTA · DESDE Analitica.Regalia
-- ---------------------------------------------------------------------
--  Lee los registros YA cerrados por `SP_CerrarFacturacionMensual`,
--  filtrados por artista (a través de la canción → álbum → artista).
--  Útil para la página de Monetización del panel del artista.
-- =====================================================================
CREATE OR ALTER PROCEDURE Pagos.sp_HistorialRegaliasArtista
    @idArtista INT,
    @desde DATE = NULL,
    @hasta DATE = NULL
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM Usuario.Artista WHERE idUsuario = @idArtista)
    BEGIN
        RAISERROR('Error: El artista no existe.', 16, 1);
        RETURN;
    END

    SELECT
        Reg.idRegalia,
        DATEFROMPARTS(Reg.anioPeriodo, Reg.mesPeriodo, 1)        AS FechaInicioPeriodo,
        EOMONTH(DATEFROMPARTS(Reg.anioPeriodo, Reg.mesPeriodo,1)) AS FechaFinPeriodo,
        Reg.mesPeriodo                                           AS Mes,
        Reg.anioPeriodo                                          AS Anio,
        C.nombreCancion                                          AS Cancion,
        Alb.tituloAlbum                                          AS Album,
        Reg.paisReproduccion                                     AS Pais,
        Reg.cantidadReproducciones                               AS Reproducciones,
        CAST(Reg.montoTotalGenerado AS DECIMAL(18,2))            AS MontoBruto,
        CAST(Reg.montoDiscografica  AS DECIMAL(18,2))            AS MontoDiscografica,
        CAST(Reg.montoArtista       AS DECIMAL(18,2))            AS MontoNetoArtista
    FROM Analitica.Regalia Reg
    INNER JOIN Catalogo.Cancion C    ON C.idCancion = Reg.Cancion_idCancion
    INNER JOIN Catalogo.Album   Alb  ON Alb.idAlbum = C.Album_idAlbum
    WHERE Alb.Artista_idUsuario = @idArtista
      AND (@desde IS NULL OR EOMONTH(DATEFROMPARTS(Reg.anioPeriodo, Reg.mesPeriodo, 1)) >= @desde)
      AND (@hasta IS NULL OR DATEFROMPARTS(Reg.anioPeriodo, Reg.mesPeriodo, 1)        <= @hasta)
    ORDER BY Reg.anioPeriodo DESC, Reg.mesPeriodo DESC, MontoNetoArtista DESC;
END
GO
GRANT EXECUTE ON Pagos.sp_HistorialRegaliasArtista TO RolArtista;
GRANT EXECUTE ON Pagos.sp_HistorialRegaliasArtista TO RolAdministrador;
GRANT EXECUTE ON Pagos.sp_HistorialRegaliasArtista TO RolReportes;
GO


-- =====================================================================
--  RESUMEN HISTÓRICO DE REGALÍAS POR MES (PARA GRÁFICO)
-- ---------------------------------------------------------------------
--  Devuelve montoNeto / montoBruto agregado por mes para un artista,
--  ideal para graficar evolución mes a mes.
-- =====================================================================
CREATE OR ALTER PROCEDURE Pagos.sp_ResumenMensualRegaliasArtista
    @idArtista INT,
    @meses INT = 12
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM Usuario.Artista WHERE idUsuario = @idArtista)
    BEGIN
        RAISERROR('Error: El artista no existe.', 16, 1);
        RETURN;
    END

    DECLARE @fechaMin DATE = DATEADD(MONTH, -@meses, CAST(GETDATE() AS DATE));

    SELECT
        Reg.anioPeriodo                                  AS Anio,
        Reg.mesPeriodo                                   AS Mes,
        FORMAT(DATEFROMPARTS(Reg.anioPeriodo, Reg.mesPeriodo, 1), 'MMM yyyy', 'es-ES') AS Etiqueta,
        SUM(Reg.cantidadReproducciones)                  AS Reproducciones,
        CAST(SUM(Reg.montoTotalGenerado) AS DECIMAL(18,2)) AS MontoBruto,
        CAST(SUM(Reg.montoDiscografica)  AS DECIMAL(18,2)) AS MontoDiscografica,
        CAST(SUM(Reg.montoArtista)       AS DECIMAL(18,2)) AS MontoNetoArtista
    FROM Analitica.Regalia Reg
    INNER JOIN Catalogo.Cancion C    ON C.idCancion = Reg.Cancion_idCancion
    INNER JOIN Catalogo.Album   Alb  ON Alb.idAlbum = C.Album_idAlbum
    WHERE Alb.Artista_idUsuario = @idArtista
      AND DATEFROMPARTS(Reg.anioPeriodo, Reg.mesPeriodo, 1) >= @fechaMin
    GROUP BY Reg.anioPeriodo, Reg.mesPeriodo
    ORDER BY Anio, Mes;
END
GO
GRANT EXECUTE ON Pagos.sp_ResumenMensualRegaliasArtista TO RolArtista;
GRANT EXECUTE ON Pagos.sp_ResumenMensualRegaliasArtista TO RolAdministrador;
GRANT EXECUTE ON Pagos.sp_ResumenMensualRegaliasArtista TO RolReportes;
GO


CREATE OR ALTER PROCEDURE Analitica.sp_AdmPeriodosPendientes
AS
BEGIN
    SET NOCOUNT ON;
    SELECT DISTINCT
        YEAR(R.fechaHora)  AS Anio,
        MONTH(R.fechaHora) AS Mes
    FROM Analitica.Reproduccion R
    WHERE NOT EXISTS (
        SELECT 1 FROM Analitica.Regalia Reg
         WHERE Reg.mesPeriodo  = MONTH(R.fechaHora)
           AND Reg.anioPeriodo = YEAR(R.fechaHora)
    )
    ORDER BY Anio, Mes;
END
GO
GRANT EXECUTE ON Analitica.sp_AdmPeriodosPendientes TO RolAdministrador;
GO
