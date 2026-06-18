"""
Modelo TipoAlbum — refleja [Catalogo].[TipoAlbum]
Clasificación de álbumes: LP, EP, Single, Compilation, etc.
"""

from django.db import models


class TipoAlbum(models.Model):
    id_tipo_album = models.AutoField(
        db_column='idTipoAlbum',
        primary_key=True,
    )
    nombre_tipo = models.CharField(
        db_column='nombreTipo',
        max_length=20,
        unique=True,
    )
    descripcion_tipo = models.TextField(
        db_column='descripcionTipo',
        blank=True,
        null=True,
    )

    class Meta:
        managed = False
        db_table = '[Catalogo].[TipoAlbum]'
        verbose_name = 'Tipo de Álbum'
        verbose_name_plural = 'Tipos de Álbum'

    def __str__(self):
        return self.nombre_tipo
