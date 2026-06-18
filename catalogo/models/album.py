"""
Modelo Album — refleja [Catalogo].[Album]

CHECKs del SQL:
  - estadoAlbum IN ('activo', 'eliminado', 'inactivo')
"""

from django.db import models
from django.core.validators import MinLengthValidator

from usuarios.models import Artista
from .tipo_album import TipoAlbum


class Album(models.Model):
    ESTADO_CHOICES = [
        ('activo',    'Activo'),
        ('inactivo',  'Inactivo'),
        ('eliminado', 'Eliminado'),
    ]

    id_album = models.AutoField(
        db_column='idAlbum',
        primary_key=True,
    )
    titulo_album = models.CharField(
        db_column='tituloAlbum',
        max_length=40,
        validators=[MinLengthValidator(2)],
    )
    fecha_lanzamiento_album = models.DateField(
        db_column='fechaLanzamientoAlbum',
    )
    descripcion_album = models.TextField(
        db_column='descripcionAlbum',
        blank=True,
        null=True,
    )
    estado_album = models.CharField(
        db_column='estadoAlbum',
        max_length=20,
        choices=ESTADO_CHOICES,
        default='activo',
    )
    tipo_album = models.ForeignKey(
        TipoAlbum,
        db_column='TipoAlbum_idTipoAlbum',
        on_delete=models.DO_NOTHING,
        related_name='albumes',
    )
    artista = models.ForeignKey(
        Artista,
        db_column='Artista_idUsuario',
        on_delete=models.DO_NOTHING,
        related_name='albumes',
    )

    class Meta:
        managed = False
        db_table = '[Catalogo].[Album]'
        ordering = ['-fecha_lanzamiento_album']
        verbose_name = 'Álbum'
        verbose_name_plural = 'Álbumes'

    def __str__(self):
        return self.titulo_album

    @property
    def es_activo(self):
        return self.estado_album == 'activo'

    @property
    def total_canciones(self):
        return self.canciones.filter(estado_cancion='activa').count()
