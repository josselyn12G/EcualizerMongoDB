"""
Modelo GeneroMusical — refleja [Catalogo].[GeneroMusical]
"""

from django.db import models


class GeneroMusical(models.Model):
    id_genero_musical = models.SmallIntegerField(
        db_column='idGeneroMusical',
        primary_key=True,
    )
    nombre_genero = models.CharField(
        db_column='nombreGenero',
        max_length=40,
        unique=True,
    )

    class Meta:
        managed = False
        db_table = '[Catalogo].[GeneroMusical]'
        ordering = ['nombre_genero']
        verbose_name = 'Género Musical'
        verbose_name_plural = 'Géneros Musicales'

    def __str__(self):
        return self.nombre_genero
