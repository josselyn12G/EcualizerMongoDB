"""
Modelo Regalia — refleja [Analitica].[Regalia]

CHECKs replicados del DDL:
  - cantidadReproducciones >= 0
  - montoTotalGenerado / montoArtista / montoDiscografica >= 0
  - mesPeriodo entre 1 y 12
  - anioPeriodo entre 2000 y año actual
"""

from datetime import date
from calendar import monthrange

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from catalogo.models import Cancion


class Regalia(models.Model):
    id_regalia = models.AutoField(
        db_column='idRegalia',
        primary_key=True,
    )
    cantidad_reproducciones = models.BigIntegerField(
        db_column='cantidadReproducciones',
        validators=[MinValueValidator(0)],
    )
    monto_total_generado = models.DecimalField(
        db_column='montoTotalGenerado',
        max_digits=18, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    monto_artista = models.DecimalField(
        db_column='montoArtista',
        max_digits=18, decimal_places=2,
        validators=[MinValueValidator(0)],
        blank=True, null=True,
    )
    monto_discografica = models.DecimalField(
        db_column='montoDiscografica',
        max_digits=18, decimal_places=2,
        validators=[MinValueValidator(0)],
        blank=True, null=True,
    )
    pais_reproduccion = models.CharField(
        db_column='paisReproduccion',
        max_length=50,
        blank=True, null=True,
    )
    mes_periodo = models.PositiveSmallIntegerField(
        db_column='mesPeriodo',
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )
    anio_periodo = models.PositiveSmallIntegerField(
        db_column='anioPeriodo',
        validators=[MinValueValidator(2000)],
    )
    cancion = models.ForeignKey(
        Cancion,
        db_column='Cancion_idCancion',
        on_delete=models.DO_NOTHING,
        related_name='regalias',
    )

    class Meta:
        managed = False
        db_table = '[Analitica].[Regalia]'
        ordering = ['-anio_periodo', '-mes_periodo']
        verbose_name = 'Regalía'
        verbose_name_plural = 'Regalías'

    def __str__(self):
        return f'Regalía #{self.id_regalia} · {self.mes_periodo}/{self.anio_periodo}'

    @property
    def fecha_inicio_periodo(self) -> date:
        return date(self.anio_periodo, self.mes_periodo, 1)

    @property
    def fecha_fin_periodo(self) -> date:
        last_day = monthrange(self.anio_periodo, self.mes_periodo)[1]
        return date(self.anio_periodo, self.mes_periodo, last_day)
