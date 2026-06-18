"""
Modelos sociales/favoritos — reflejan tablas del esquema [Biblioteca].

Estructura del DDL:
  - [Biblioteca].[UsuarioCancionLike]   (Usuario_idUsuario, Cancion_idCancion, fechaLike)
  - [Biblioteca].[UsuarioSigueArtista]  (Usuario_idUsuario, Artista_idUsuario, fechaSeguimiento, notificacionesActivas)
  - [Biblioteca].[UsuarioAlbum]         (Usuario_idUsuario, Album_idAlbum, fechaGuardado)

Todas tienen PK compuesta → unicidad garantizada por la BD
(no se puede dar like dos veces a la misma canción, etc.).
"""

from django.db import models


class UsuarioCancionLike(models.Model):
    usuario_id = models.IntegerField(db_column='Usuario_idUsuario')
    cancion_id = models.IntegerField(db_column='Cancion_idCancion')
    fecha_like = models.DateTimeField(db_column='fechaLike', auto_now_add=True)

    class Meta:
        managed = False
        db_table = '[Biblioteca].[UsuarioCancionLike]'
        # PK compuesta (Django no soporta nativo, pero la BD la enforza)
        unique_together = (('usuario_id', 'cancion_id'),)


class UsuarioSigueArtista(models.Model):
    usuario_id = models.IntegerField(db_column='Usuario_idUsuario')
    artista_id = models.IntegerField(db_column='Artista_idUsuario')
    fecha_seguimiento = models.DateField(db_column='fechaSeguimiento', auto_now_add=True)
    notificaciones_activas = models.CharField(
        db_column='notificacionesActivas',
        max_length=1,
        default='A',
        choices=[('A', 'Activas'), ('D', 'Desactivadas')],
    )

    class Meta:
        managed = False
        db_table = '[Biblioteca].[UsuarioSigueArtista]'
        unique_together = (('usuario_id', 'artista_id'),)


class UsuarioAlbum(models.Model):
    """Álbumes guardados por el usuario (Biblioteca.UsuarioAlbum)."""
    usuario_id = models.IntegerField(db_column='Usuario_idUsuario')
    album_id = models.IntegerField(db_column='Album_idAlbum')
    fecha_guardado = models.DateField(db_column='fechaGuardado', auto_now_add=True)

    class Meta:
        managed = False
        db_table = '[Biblioteca].[UsuarioAlbum]'
        unique_together = (('usuario_id', 'album_id'),)
