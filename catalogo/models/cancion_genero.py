"""
Modelo CancionGeneroMusical — refleja [Catalogo].[CancionGeneroMusical]
Tabla intermedia M:N entre Cancion y GeneroMusical.
PK compuesta (Cancion_idCancion, GeneroMusical_idGeneroMusical).
"""

from django.db import models

from .cancion import Cancion
from .genero_musical import GeneroMusical


class CancionGeneroMusical(models.Model):
    # PK compuesta — Django no soporta nativo, declaramos cancion como PK
    # y unique_together para emular la compuesta. El SQL ya tiene la PK real.
    cancion = models.ForeignKey(
        Cancion,
        db_column='Cancion_idCancion',
        on_delete=models.DO_NOTHING,
        primary_key=True,
        related_name='cancion_generos',
    )
    genero_musical = models.ForeignKey(
        GeneroMusical,
        db_column='GeneroMusical_idGeneroMusical',
        on_delete=models.DO_NOTHING,
        related_name='genero_canciones',
    )

    class Meta:
        managed = False
        db_table = '[Catalogo].[CancionGeneroMusical]'
        unique_together = (('cancion', 'genero_musical'),)
        verbose_name = 'Canción - Género Musical'
        verbose_name_plural = 'Canciones - Géneros Musicales'

    def __str__(self):
        return f'{self.cancion} · {self.genero_musical}'
