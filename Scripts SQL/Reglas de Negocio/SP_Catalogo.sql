-- =====================================================================
--          STORED PROCEDURES — ESQUEMA [Catalogo]
--          App Django: catalogo/
-- =====================================================================
-- Ejecutar con: USE Ecualizer; GO   antes de cada bloque.
-- Incluye 10 SPs + 1 tabla auxiliar de reportes.
-- =====================================================================

USE Ecualizer;
GO

-- ---------------------------------------------------------------------
-- TABLA AUXILIAR para guardar reportes (admin → artista)
-- ---------------------------------------------------------------------
IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'ReporteCancion'
               AND SCHEMA_NAME(schema_id) = 'Catalogo')
BEGIN
    CREATE TABLE Catalogo.ReporteCancion (
        idReporte           INT IDENTITY(1,1) NOT NULL,
        Cancion_idCancion   INT NOT NULL,
        Admin_idUsuario     INT NOT NULL,
        motivo              VARCHAR(100) NOT NULL,
        comentario          VARCHAR(MAX) NOT NULL,
        fechaReporte        DATETIME NOT NULL DEFAULT GETDATE(),
        CONSTRAINT ReporteCancion_PK PRIMARY KEY CLUSTERED (idReporte),
        CONSTRAINT ReporteCancion_Cancion_FK FOREIGN KEY (Cancion_idCancion)
            REFERENCES Catalogo.Cancion (idCancion),
        CONSTRAINT ReporteCancion_Admin_FK FOREIGN KEY (Admin_idUsuario)
            REFERENCES Usuario.Administrador (idUsuario)
    );
END
GO


-- =====================================================================
--                 SP 1 · Catalogo.SP_CrearAlbum
-- =====================================================================
-- Llamado desde: catalogo/services/album_service.py → sp_crear_album()
-- Usado en    : ArtistaAlbumCreateView
CREATE OR ALTER PROCEDURE Catalogo.SP_CrearAlbum
    @tituloAlbum             VARCHAR(40),
    @fechaLanzamientoAlbum   DATE,
    @descripcionAlbum        VARCHAR(MAX) = NULL,
    @TipoAlbum_idTipoAlbum   TINYINT,
    @Artista_idUsuario       INT
AS
BEGIN
    SET NOCOUNT ON;

    -- Validaciones
    IF LEN(LTRIM(@tituloAlbum)) < 2
        THROW 50101, 'El titulo del album debe tener al menos 2 caracteres.', 1;

    IF NOT EXISTS (SELECT 1 FROM Usuario.Artista WHERE idUsuario = @Artista_idUsuario)
        THROW 50102, 'El artista no existe.', 1;

    IF NOT EXISTS (SELECT 1 FROM Catalogo.TipoAlbum WHERE idTipoAlbum = @TipoAlbum_idTipoAlbum)
        THROW 50103, 'El tipo de album no es valido.', 1;

    BEGIN TRY
        BEGIN TRANSACTION;

        INSERT INTO Catalogo.Album
            (tituloAlbum, fechaLanzamientoAlbum, descripcionAlbum,
             estadoAlbum, TipoAlbum_idTipoAlbum, Artista_idUsuario)
        VALUES
            (@tituloAlbum, @fechaLanzamientoAlbum, @descripcionAlbum,
             'activo', @TipoAlbum_idTipoAlbum, @Artista_idUsuario);

        DECLARE @idAlbum INT = SCOPE_IDENTITY();

        COMMIT TRANSACTION;

        SELECT @idAlbum AS idAlbum;  -- devuelve el id al servicio Python
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


-- =====================================================================
--                 SP 2 · Catalogo.SP_EditarAlbum
-- =====================================================================
-- Llamado desde: catalogo/services/album_service.py → sp_editar_album()
-- Usado en    : ArtistaAlbumUpdateView, AdminAlbumUpdateView
CREATE OR ALTER PROCEDURE Catalogo.SP_EditarAlbum
    @idAlbum                 INT,
    @tituloAlbum             VARCHAR(40),
    @fechaLanzamientoAlbum   DATE,
    @descripcionAlbum        VARCHAR(MAX) = NULL,
    @TipoAlbum_idTipoAlbum   TINYINT,
    @estadoAlbum             VARCHAR(20)  = NULL,
    @Artista_idUsuario       INT          = NULL  -- si viene, valida ownership
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM Catalogo.Album WHERE idAlbum = @idAlbum)
        THROW 50111, 'El album no existe.', 1;

    -- Validar ownership cuando viene el artista
    IF @Artista_idUsuario IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM Catalogo.Album
                       WHERE idAlbum = @idAlbum AND Artista_idUsuario = @Artista_idUsuario)
        THROW 50112, 'No puedes editar un album que no te pertenece.', 1;

    IF @estadoAlbum IS NOT NULL
       AND @estadoAlbum NOT IN ('activo', 'inactivo', 'eliminado')
        THROW 50113, 'Estado de album invalido.', 1;

    BEGIN TRY
        BEGIN TRANSACTION;

        UPDATE Catalogo.Album
        SET tituloAlbum            = @tituloAlbum,
            fechaLanzamientoAlbum  = @fechaLanzamientoAlbum,
            descripcionAlbum       = @descripcionAlbum,
            TipoAlbum_idTipoAlbum  = @TipoAlbum_idTipoAlbum,
            estadoAlbum            = ISNULL(@estadoAlbum, estadoAlbum)
        WHERE idAlbum = @idAlbum;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


-- =====================================================================
--                 SP 3 · Catalogo.SP_ListarAlbumes
-- =====================================================================
-- Llamado desde: catalogo/services/album_service.py → sp_listar_albumes()
-- Usado en    : ArtistaAlbumListView, UsuarioAlbumListView, AdminAlbumListView
CREATE OR ALTER PROCEDURE Catalogo.SP_ListarAlbumes
    @Artista_idUsuario   INT          = NULL,
    @estadoAlbum         VARCHAR(20)  = NULL,
    @busqueda            VARCHAR(100) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        A.idAlbum,
        A.tituloAlbum,
        A.fechaLanzamientoAlbum,
        A.descripcionAlbum,
        A.estadoAlbum,
        TA.idTipoAlbum,
        TA.nombreTipo,
        Art.idUsuario        AS Artista_idUsuario,
        Art.nombreArtistico
    FROM Catalogo.Album         A
    INNER JOIN Catalogo.TipoAlbum  TA  ON TA.idTipoAlbum = A.TipoAlbum_idTipoAlbum
    INNER JOIN Usuario.Artista     Art ON Art.idUsuario  = A.Artista_idUsuario
    WHERE (@Artista_idUsuario IS NULL OR A.Artista_idUsuario = @Artista_idUsuario)
      AND (@estadoAlbum       IS NULL OR A.estadoAlbum       = @estadoAlbum)
      AND (@busqueda          IS NULL OR A.tituloAlbum LIKE '%' + @busqueda + '%')
    ORDER BY A.fechaLanzamientoAlbum DESC;
END;
GO


-- =====================================================================
--                 SP 4 · Catalogo.SP_DesactivarAlbum
-- =====================================================================
-- Llamado desde: catalogo/services/album_service.py → sp_desactivar_album()
-- Usado en    : ArtistaAlbumDeactivateView, AdminAlbumReportView
CREATE OR ALTER PROCEDURE Catalogo.SP_DesactivarAlbum
    @idAlbum   INT,
    @ejecutor  INT
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM Catalogo.Album WHERE idAlbum = @idAlbum)
        THROW 50121, 'El album no existe.', 1;

    BEGIN TRY
        BEGIN TRANSACTION;

        UPDATE Catalogo.Album
        SET estadoAlbum = 'inactivo'
        WHERE idAlbum = @idAlbum;

        -- Cascada: desactivar todas las canciones del album
        UPDATE Catalogo.Cancion
        SET estadoCancion = 'inactiva'
        WHERE Album_idAlbum = @idAlbum AND estadoCancion = 'activa';

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


-- =====================================================================
--                 SP 5 · Catalogo.SP_CrearCancion
-- =====================================================================
-- Llamado desde: catalogo/services/cancion_service.py → sp_crear_cancion()
-- Usado en    : ArtistaCancionCreateView
CREATE OR ALTER PROCEDURE Catalogo.SP_CrearCancion
    @nombreCancion     VARCHAR(150),
    @duracion          SMALLINT,
    @fechaLanzamiento  DATE,
    @calidadKbps       SMALLINT,
    @letraCancion      VARCHAR(MAX) = NULL,
    @Album_idAlbum     INT,
    @numeroPista       SMALLINT,
    @generos           VARCHAR(200) = ''   -- CSV: '1,4,7'
AS
BEGIN
    SET NOCOUNT ON;

    -- Validaciones
    IF @duracion <= 0
        THROW 50201, 'La duracion debe ser mayor a 0.', 1;
    IF @calidadKbps NOT IN (128, 192, 256, 320)
        THROW 50202, 'La calidad debe ser 128, 192, 256 o 320.', 1;
    IF @numeroPista <= 0
        THROW 50203, 'El numero de pista debe ser mayor a 0.', 1;
    IF NOT EXISTS (SELECT 1 FROM Catalogo.Album WHERE idAlbum = @Album_idAlbum)
        THROW 50204, 'El album no existe.', 1;

    BEGIN TRY
        BEGIN TRANSACTION;

        INSERT INTO Catalogo.Cancion
            (nombreCancion, duracion, fechaLanzamiento, estadoCancion,
             calidadKbps, totalReproducciones, letraCancion,
             Album_idAlbum, numeroPista)
        VALUES
            (@nombreCancion, @duracion, @fechaLanzamiento, 'activa',
             @calidadKbps, 0, @letraCancion,
             @Album_idAlbum, @numeroPista);

        DECLARE @idCancion INT = SCOPE_IDENTITY();

        -- Asociar generos via CSV
        IF @generos IS NOT NULL AND LEN(@generos) > 0
        BEGIN
            INSERT INTO Catalogo.CancionGeneroMusical (Cancion_idCancion, GeneroMusical_idGeneroMusical)
            SELECT @idCancion, TRY_CAST(value AS TINYINT)
            FROM STRING_SPLIT(@generos, ',')
            WHERE TRY_CAST(value AS TINYINT) IS NOT NULL
              AND EXISTS (SELECT 1 FROM Catalogo.GeneroMusical
                          WHERE idGeneroMusical = TRY_CAST(value AS TINYINT));
        END

        COMMIT TRANSACTION;

        SELECT @idCancion AS idCancion;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


-- =====================================================================
--                 SP 6 · Catalogo.SP_EditarCancion
-- =====================================================================
-- Llamado desde: catalogo/services/cancion_service.py → sp_editar_cancion()
-- Usado en    : ArtistaCancionUpdateView, AdminCancionUpdateView
CREATE OR ALTER PROCEDURE Catalogo.SP_EditarCancion
    @idCancion          INT,
    @nombreCancion      VARCHAR(150),
    @duracion           SMALLINT,
    @fechaLanzamiento   DATE,
    @calidadKbps        SMALLINT,
    @letraCancion       VARCHAR(MAX) = NULL,
    @numeroPista        SMALLINT,
    @estadoCancion      VARCHAR(20)  = NULL,
    @generos            VARCHAR(200) = NULL,
    @Artista_idUsuario  INT          = NULL
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM Catalogo.Cancion WHERE idCancion = @idCancion)
        THROW 50211, 'La cancion no existe.', 1;

    -- Ownership
    IF @Artista_idUsuario IS NOT NULL
       AND NOT EXISTS (
            SELECT 1 FROM Catalogo.Cancion C
            INNER JOIN Catalogo.Album A ON A.idAlbum = C.Album_idAlbum
            WHERE C.idCancion = @idCancion AND A.Artista_idUsuario = @Artista_idUsuario
       )
        THROW 50212, 'No puedes editar una cancion que no te pertenece.', 1;

    IF @duracion <= 0
        THROW 50213, 'La duracion debe ser mayor a 0.', 1;
    IF @calidadKbps NOT IN (128, 192, 256, 320)
        THROW 50214, 'La calidad debe ser 128, 192, 256 o 320.', 1;
    IF @numeroPista <= 0
        THROW 50215, 'El numero de pista debe ser mayor a 0.', 1;
    IF @estadoCancion IS NOT NULL
       AND @estadoCancion NOT IN ('activa', 'inactiva', 'bloqueada', 'eliminada')
        THROW 50216, 'Estado de cancion invalido.', 1;

    BEGIN TRY
        BEGIN TRANSACTION;

        UPDATE Catalogo.Cancion
        SET nombreCancion     = @nombreCancion,
            duracion          = @duracion,
            fechaLanzamiento  = @fechaLanzamiento,
            calidadKbps       = @calidadKbps,
            letraCancion      = @letraCancion,
            numeroPista       = @numeroPista,
            estadoCancion     = ISNULL(@estadoCancion, estadoCancion)
        WHERE idCancion = @idCancion;

        -- Si se enviaron generos, reemplaza la relacion completa
        IF @generos IS NOT NULL
        BEGIN
            DELETE FROM Catalogo.CancionGeneroMusical
            WHERE Cancion_idCancion = @idCancion;

            IF LEN(@generos) > 0
            BEGIN
                INSERT INTO Catalogo.CancionGeneroMusical (Cancion_idCancion, GeneroMusical_idGeneroMusical)
                SELECT @idCancion, TRY_CAST(value AS TINYINT)
                FROM STRING_SPLIT(@generos, ',')
                WHERE TRY_CAST(value AS TINYINT) IS NOT NULL
                  AND EXISTS (SELECT 1 FROM Catalogo.GeneroMusical
                              WHERE idGeneroMusical = TRY_CAST(value AS TINYINT));
            END
        END

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


-- =====================================================================
--                 SP 7 · Catalogo.SP_ListarCanciones
-- =====================================================================
-- Llamado desde: catalogo/services/cancion_service.py → sp_listar_canciones()
-- Usado en    : ArtistaCancionListView, UsuarioCancionListView, AdminCancionListView
CREATE OR ALTER PROCEDURE Catalogo.SP_ListarCanciones
    @Artista_idUsuario  INT          = NULL,
    @Album_idAlbum      INT          = NULL,
    @estadoCancion      VARCHAR(20)  = NULL,
    @busqueda           VARCHAR(150) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        C.idCancion,
        C.nombreCancion,
        C.duracion,
        C.fechaLanzamiento,
        C.estadoCancion,
        C.calidadKbps,
        C.totalReproducciones,
        C.numeroPista,
        C.Album_idAlbum,
        A.tituloAlbum,
        Art.idUsuario        AS Artista_idUsuario,
        Art.nombreArtistico
    FROM Catalogo.Cancion       C
    INNER JOIN Catalogo.Album    A   ON A.idAlbum   = C.Album_idAlbum
    INNER JOIN Usuario.Artista   Art ON Art.idUsuario = A.Artista_idUsuario
    WHERE (@Artista_idUsuario IS NULL OR A.Artista_idUsuario = @Artista_idUsuario)
      AND (@Album_idAlbum     IS NULL OR C.Album_idAlbum     = @Album_idAlbum)
      AND (@estadoCancion     IS NULL OR C.estadoCancion     = @estadoCancion)
      AND (@busqueda          IS NULL OR C.nombreCancion LIKE '%' + @busqueda + '%')
    ORDER BY A.tituloAlbum, C.numeroPista;
END;
GO


-- =====================================================================
--                 SP 8 · Catalogo.SP_FiltrarCancionesGenero
-- =====================================================================
-- Llamado desde: catalogo/services/cancion_service.py → sp_filtrar_canciones_genero()
-- Usado en    : UsuarioCancionFilterView
CREATE OR ALTER PROCEDURE Catalogo.SP_FiltrarCancionesGenero
    @idGeneroMusical TINYINT
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM Catalogo.GeneroMusical WHERE idGeneroMusical = @idGeneroMusical)
        THROW 50301, 'El genero musical no existe.', 1;

    SELECT
        C.idCancion,
        C.nombreCancion,
        C.duracion,
        C.calidadKbps,
        C.totalReproducciones,
        A.tituloAlbum,
        Art.nombreArtistico
    FROM Catalogo.Cancion               C
    INNER JOIN Catalogo.Album            A   ON A.idAlbum   = C.Album_idAlbum
    INNER JOIN Usuario.Artista           Art ON Art.idUsuario = A.Artista_idUsuario
    INNER JOIN Catalogo.CancionGeneroMusical CGM ON CGM.Cancion_idCancion = C.idCancion
    WHERE CGM.GeneroMusical_idGeneroMusical = @idGeneroMusical
      AND C.estadoCancion = 'activa'
      AND A.estadoAlbum   = 'activo'
    ORDER BY C.totalReproducciones DESC;
END;
GO


-- =====================================================================
--                 SP 9 · Catalogo.SP_DesactivarCancion
-- =====================================================================
-- Llamado desde: catalogo/services/cancion_service.py → sp_desactivar_cancion()
-- Usado en    : ArtistaCancionDeactivateView, AdminCancionDeactivateView
CREATE OR ALTER PROCEDURE Catalogo.SP_DesactivarCancion
    @idCancion  INT,
    @ejecutor   INT
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM Catalogo.Cancion WHERE idCancion = @idCancion)
        THROW 50311, 'La cancion no existe.', 1;

    BEGIN TRY
        BEGIN TRANSACTION;

        UPDATE Catalogo.Cancion
        SET estadoCancion = 'inactiva'
        WHERE idCancion = @idCancion;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


-- =====================================================================
--                 SP 10 · Catalogo.SP_ReportarCancion
-- =====================================================================
-- Llamado desde: catalogo/services/cancion_service.py → sp_reportar_cancion()
-- Usado en    : AdminCancionReportView
-- Graba en Catalogo.ReporteCancion y marca la cancion como 'bloqueada'.
CREATE OR ALTER PROCEDURE Catalogo.SP_ReportarCancion
    @idCancion   INT,
    @idAdmin     INT,
    @motivo      VARCHAR(100),
    @comentario  VARCHAR(MAX)
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM Catalogo.Cancion WHERE idCancion = @idCancion)
        THROW 50401, 'La cancion no existe.', 1;
    IF NOT EXISTS (SELECT 1 FROM Usuario.Administrador WHERE idUsuario = @idAdmin)
        THROW 50402, 'El administrador no existe.', 1;
    IF LEN(LTRIM(@motivo)) = 0
        THROW 50403, 'El motivo no puede estar vacio.', 1;
    IF LEN(LTRIM(@comentario)) = 0
        THROW 50404, 'El comentario no puede estar vacio.', 1;

    BEGIN TRY
        BEGIN TRANSACTION;

        INSERT INTO Catalogo.ReporteCancion
            (Cancion_idCancion, Admin_idUsuario, motivo, comentario, fechaReporte)
        VALUES (@idCancion, @idAdmin, @motivo, @comentario, GETDATE());

        -- Bloquea automaticamente la cancion al ser reportada
        UPDATE Catalogo.Cancion
        SET estadoCancion = 'bloqueada'
        WHERE idCancion = @idCancion;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


-- =====================================================================
--                          GRANTS (RBAC)
-- =====================================================================
-- Ajusta a los roles definidos en UsuariosRolesBDD.sql
GRANT EXECUTE ON Catalogo.SP_CrearAlbum           TO RolArtista;
GRANT EXECUTE ON Catalogo.SP_EditarAlbum          TO RolArtista, RolAdministrador;
GRANT EXECUTE ON Catalogo.SP_ListarAlbumes        TO RolArtista, RolOyente, RolAdministrador;
GRANT EXECUTE ON Catalogo.SP_DesactivarAlbum      TO RolArtista, RolAdministrador;

GRANT EXECUTE ON Catalogo.SP_CrearCancion         TO RolArtista;
GRANT EXECUTE ON Catalogo.SP_EditarCancion        TO RolArtista, RolAdministrador;
GRANT EXECUTE ON Catalogo.SP_ListarCanciones      TO RolArtista, RolOyente, RolAdministrador;
GRANT EXECUTE ON Catalogo.SP_FiltrarCancionesGenero TO RolOyente, RolArtista, RolAdministrador;
GRANT EXECUTE ON Catalogo.SP_DesactivarCancion    TO RolArtista, RolAdministrador;
GRANT EXECUTE ON Catalogo.SP_ReportarCancion      TO RolAdministrador;
GO
