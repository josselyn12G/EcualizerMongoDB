-- =====================================================================
--          STORED PROCEDURES — ESQUEMA [Catalogo] · v2
--          Generos, TipoAlbum y M:N Cancion↔Genero
-- =====================================================================
-- Complementa SP_Catalogo.sql con:
--   - SP_CrearGenero / SP_EditarGenero / SP_EliminarGenero / SP_ListarGeneros
--   - SP_CrearTipoAlbum / SP_EditarTipoAlbum / SP_EliminarTipoAlbum / SP_ListarTiposAlbum
--   - SP_AgregarGeneroACancion / SP_QuitarGeneroDeCancion
--   - SP_GenerosDeCancion · lista los géneros asociados a UNA canción
--   - SP_ListarCancionesConGeneros · variante que incluye CSV de géneros por canción
-- =====================================================================

USE Ecualizer;
GO

-- =====================================================================
--                 GeneroMusical · CRUD
-- =====================================================================
-- Nota: la tabla GeneroMusical NO tiene IDENTITY → el SP calcula el siguiente id.
-- =====================================================================

CREATE OR ALTER PROCEDURE Catalogo.SP_ListarGeneros
    @busqueda VARCHAR(40) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        G.idGeneroMusical,
        G.nombreGenero,
        (SELECT COUNT(*) FROM Catalogo.CancionGeneroMusical CGM
         WHERE CGM.GeneroMusical_idGeneroMusical = G.idGeneroMusical) AS totalCanciones
    FROM Catalogo.GeneroMusical G
    WHERE (@busqueda IS NULL OR G.nombreGenero LIKE '%' + @busqueda + '%')
    ORDER BY G.nombreGenero;
END;
GO


CREATE OR ALTER PROCEDURE Catalogo.SP_CrearGenero
    @nombreGenero VARCHAR(40)
AS
BEGIN
    SET NOCOUNT ON;

    IF LEN(LTRIM(@nombreGenero)) < 2
        THROW 50501, 'El nombre del genero debe tener al menos 2 caracteres.', 1;
    IF EXISTS (SELECT 1 FROM Catalogo.GeneroMusical WHERE nombreGenero = @nombreGenero)
        THROW 50502, 'Ya existe un genero con ese nombre.', 1;

    BEGIN TRY
        BEGIN TRANSACTION;

        DECLARE @nextId TINYINT;
        SELECT @nextId = ISNULL(MAX(idGeneroMusical), 0) + 1
        FROM Catalogo.GeneroMusical;

        IF @nextId > 255
            THROW 50503, 'Se alcanzo el limite de generos (255).', 1;

        INSERT INTO Catalogo.GeneroMusical (idGeneroMusical, nombreGenero)
        VALUES (@nextId, @nombreGenero);

        COMMIT TRANSACTION;
        SELECT @nextId AS idGeneroMusical;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH
END;
GO


CREATE OR ALTER PROCEDURE Catalogo.SP_EditarGenero
    @idGeneroMusical TINYINT,
    @nombreGenero    VARCHAR(40)
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM Catalogo.GeneroMusical WHERE idGeneroMusical = @idGeneroMusical)
        THROW 50511, 'El genero no existe.', 1;
    IF LEN(LTRIM(@nombreGenero)) < 2
        THROW 50512, 'El nombre debe tener al menos 2 caracteres.', 1;
    IF EXISTS (SELECT 1 FROM Catalogo.GeneroMusical
               WHERE nombreGenero = @nombreGenero AND idGeneroMusical <> @idGeneroMusical)
        THROW 50513, 'Ya existe otro genero con ese nombre.', 1;

    UPDATE Catalogo.GeneroMusical
    SET nombreGenero = @nombreGenero
    WHERE idGeneroMusical = @idGeneroMusical;
END;
GO


CREATE OR ALTER PROCEDURE Catalogo.SP_EliminarGenero
    @idGeneroMusical TINYINT
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM Catalogo.GeneroMusical WHERE idGeneroMusical = @idGeneroMusical)
        THROW 50521, 'El genero no existe.', 1;

    -- Validar que no esté en uso
    IF EXISTS (SELECT 1 FROM Catalogo.CancionGeneroMusical
               WHERE GeneroMusical_idGeneroMusical = @idGeneroMusical)
        THROW 50522, 'No se puede eliminar: hay canciones asociadas a este genero.', 1;

    DELETE FROM Catalogo.GeneroMusical
    WHERE idGeneroMusical = @idGeneroMusical;
END;
GO


-- =====================================================================
--                 TipoAlbum · CRUD
-- =====================================================================

CREATE OR ALTER PROCEDURE Catalogo.SP_ListarTiposAlbum
    @busqueda VARCHAR(20) = NULL
AS
BEGIN
    SET NOCOUNT ON;
    SELECT
        TA.idTipoAlbum,
        TA.nombreTipo,
        TA.descripcionTipo,
        (SELECT COUNT(*) FROM Catalogo.Album A
         WHERE A.TipoAlbum_idTipoAlbum = TA.idTipoAlbum) AS totalAlbumes
    FROM Catalogo.TipoAlbum TA
    WHERE (@busqueda IS NULL OR TA.nombreTipo LIKE '%' + @busqueda + '%')
    ORDER BY TA.nombreTipo;
END;
GO


CREATE OR ALTER PROCEDURE Catalogo.SP_CrearTipoAlbum
    @nombreTipo       VARCHAR(20),
    @descripcionTipo  VARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    IF LEN(LTRIM(@nombreTipo)) < 2
        THROW 50601, 'El nombre del tipo debe tener al menos 2 caracteres.', 1;
    IF EXISTS (SELECT 1 FROM Catalogo.TipoAlbum WHERE nombreTipo = @nombreTipo)
        THROW 50602, 'Ya existe un tipo de album con ese nombre.', 1;

    INSERT INTO Catalogo.TipoAlbum (nombreTipo, descripcionTipo)
    VALUES (@nombreTipo, @descripcionTipo);

    SELECT SCOPE_IDENTITY() AS idTipoAlbum;
END;
GO


CREATE OR ALTER PROCEDURE Catalogo.SP_EditarTipoAlbum
    @idTipoAlbum      TINYINT,
    @nombreTipo       VARCHAR(20),
    @descripcionTipo  VARCHAR(MAX) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM Catalogo.TipoAlbum WHERE idTipoAlbum = @idTipoAlbum)
        THROW 50611, 'El tipo de album no existe.', 1;
    IF LEN(LTRIM(@nombreTipo)) < 2
        THROW 50612, 'El nombre debe tener al menos 2 caracteres.', 1;
    IF EXISTS (SELECT 1 FROM Catalogo.TipoAlbum
               WHERE nombreTipo = @nombreTipo AND idTipoAlbum <> @idTipoAlbum)
        THROW 50613, 'Ya existe otro tipo con ese nombre.', 1;

    UPDATE Catalogo.TipoAlbum
    SET nombreTipo      = @nombreTipo,
        descripcionTipo = @descripcionTipo
    WHERE idTipoAlbum = @idTipoAlbum;
END;
GO


CREATE OR ALTER PROCEDURE Catalogo.SP_EliminarTipoAlbum
    @idTipoAlbum TINYINT
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM Catalogo.TipoAlbum WHERE idTipoAlbum = @idTipoAlbum)
        THROW 50621, 'El tipo de album no existe.', 1;

    IF EXISTS (SELECT 1 FROM Catalogo.Album WHERE TipoAlbum_idTipoAlbum = @idTipoAlbum)
        THROW 50622, 'No se puede eliminar: hay albumes asociados a este tipo.', 1;

    DELETE FROM Catalogo.TipoAlbum WHERE idTipoAlbum = @idTipoAlbum;
END;
GO


-- =====================================================================
--                 M:N · Cancion ↔ Genero
-- =====================================================================

CREATE OR ALTER PROCEDURE Catalogo.SP_AgregarGeneroACancion
    @idCancion       INT,
    @idGeneroMusical TINYINT
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM Catalogo.Cancion WHERE idCancion = @idCancion)
        THROW 50701, 'La cancion no existe.', 1;
    IF NOT EXISTS (SELECT 1 FROM Catalogo.GeneroMusical WHERE idGeneroMusical = @idGeneroMusical)
        THROW 50702, 'El genero no existe.', 1;
    IF EXISTS (SELECT 1 FROM Catalogo.CancionGeneroMusical
               WHERE Cancion_idCancion = @idCancion
                 AND GeneroMusical_idGeneroMusical = @idGeneroMusical)
        THROW 50703, 'Esta cancion ya tiene asociado ese genero.', 1;

    INSERT INTO Catalogo.CancionGeneroMusical (Cancion_idCancion, GeneroMusical_idGeneroMusical)
    VALUES (@idCancion, @idGeneroMusical);
END;
GO


CREATE OR ALTER PROCEDURE Catalogo.SP_QuitarGeneroDeCancion
    @idCancion       INT,
    @idGeneroMusical TINYINT
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM Catalogo.CancionGeneroMusical
                   WHERE Cancion_idCancion = @idCancion
                     AND GeneroMusical_idGeneroMusical = @idGeneroMusical)
        THROW 50711, 'Esa relacion cancion-genero no existe.', 1;

    DELETE FROM Catalogo.CancionGeneroMusical
    WHERE Cancion_idCancion = @idCancion
      AND GeneroMusical_idGeneroMusical = @idGeneroMusical;
END;
GO


-- Devuelve los géneros asociados a UNA canción.
CREATE OR ALTER PROCEDURE Catalogo.SP_GenerosDeCancion
    @idCancion INT
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        G.idGeneroMusical,
        G.nombreGenero
    FROM Catalogo.CancionGeneroMusical CGM
    INNER JOIN Catalogo.GeneroMusical   G ON G.idGeneroMusical = CGM.GeneroMusical_idGeneroMusical
    WHERE CGM.Cancion_idCancion = @idCancion
    ORDER BY G.nombreGenero;
END;
GO


-- Variante de SP_ListarCanciones que incluye un CSV con los géneros.
-- Útil para mostrar badges directamente en la tabla del admin.
CREATE OR ALTER PROCEDURE Catalogo.SP_ListarCancionesConGeneros
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
        Art.nombreArtistico,
        STUFF((
            SELECT ', ' + G.nombreGenero
            FROM Catalogo.CancionGeneroMusical CGM
            INNER JOIN Catalogo.GeneroMusical G ON G.idGeneroMusical = CGM.GeneroMusical_idGeneroMusical
            WHERE CGM.Cancion_idCancion = C.idCancion
            ORDER BY G.nombreGenero
            FOR XML PATH(''), TYPE
        ).value('.', 'NVARCHAR(MAX)'), 1, 2, '') AS generosCSV
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
--                          GRANTS
-- =====================================================================
GRANT EXECUTE ON Catalogo.SP_ListarGeneros           TO RolAdministrador, RolArtista, RolOyente;
GRANT EXECUTE ON Catalogo.SP_CrearGenero             TO RolAdministrador;
GRANT EXECUTE ON Catalogo.SP_EditarGenero            TO RolAdministrador;
GRANT EXECUTE ON Catalogo.SP_EliminarGenero          TO RolAdministrador;

GRANT EXECUTE ON Catalogo.SP_ListarTiposAlbum        TO RolAdministrador, RolArtista, RolOyente;
GRANT EXECUTE ON Catalogo.SP_CrearTipoAlbum          TO RolAdministrador;
GRANT EXECUTE ON Catalogo.SP_EditarTipoAlbum         TO RolAdministrador;
GRANT EXECUTE ON Catalogo.SP_EliminarTipoAlbum       TO RolAdministrador;

GRANT EXECUTE ON Catalogo.SP_AgregarGeneroACancion   TO RolAdministrador, RolArtista;
GRANT EXECUTE ON Catalogo.SP_QuitarGeneroDeCancion   TO RolAdministrador, RolArtista;
GRANT EXECUTE ON Catalogo.SP_GenerosDeCancion        TO RolAdministrador, RolArtista, RolOyente;
GRANT EXECUTE ON Catalogo.SP_ListarCancionesConGeneros TO RolAdministrador, RolArtista, RolOyente;
GO
