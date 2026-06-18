"""
Modelo Reproduccion — refleja [Analitica].[Reproduccion]

PK COMPUESTA: (Usuario_idUsuario, Cancion_idCancion, idReproduccion).
Django no soporta PK compuestas nativas; declaramos `id_reproduccion`
como PK (AutoField IDENTITY) y emulamos la compuesta con `unique_together`.
La PK real la enforza SQL Server.
"""

from django.db import models
from django.core.validators import MinValueValidator

from usuarios.models import Usuario
from catalogo.models import Cancion


class Reproduccion(models.Model):
    FLAG_CHOICES = [('N', 'No saltada'), ('S', 'Saltada')]

    id_reproduccion = models.AutoField(
        db_column='idReproduccion',
        primary_key=True,
    )
    usuario = models.ForeignKey(
        Usuario,
        db_column='Usuario_idUsuario',
        on_delete=models.DO_NOTHING,
        related_name='reproducciones',
    )
    cancion = models.ForeignKey(
        Cancion,
        db_column='Cancion_idCancion',
        on_delete=models.DO_NOTHING,
        related_name='reproducciones',
    )
    fecha_hora = models.DateTimeField(
        db_column='fechaHora',
        auto_now_add=True,
    )
    pais = models.CharField(
        db_column='pais',
        max_length=50,
        blank=True,
        null=True,
    )
    duracion_escuchada = models.SmallIntegerField(
        db_column='duracionEscuchada',
        validators=[MinValueValidator(1)],
        help_text='Segundos escuchados (> 0).',
    )
    fue_saltada = models.CharField(
        db_column='fueSaltada',
        max_length=1,
        choices=FLAG_CHOICES,
        default='N',
    )

    class Meta:
        managed = False
        db_table = '[Analitica].[Reproduccion]'
        unique_together = (('usuario', 'cancion', 'id_reproduccion'),)
        ordering = ['-fecha_hora']
        verbose_name = 'Reproducción'
        verbose_name_plural = 'Reproducciones'

    def __str__(self):
        return f'{self.usuario_id} → {self.cancion_id} @ {self.fecha_hora:%Y-%m-%d %H:%M}'

    @property
    def es_skip(self) -> bool:
        return self.fue_saltada == 'S'
