"""
Modelo ContratoDiscografica — refleja [Industria].[ContratoDiscografica]

PK compuesta: (Artista_idUsuario, Discografica_idDiscografica, idContrato)
Django no soporta PK compuestas nativas; usamos idContrato como AutoField PK
y agregamos unique_together para emular la compuesta. La PK real la enforza
SQL Server.

CHECKs:
  - fechaFin > fechaInicio
  - porcentajeArtista       ∈ [0, 100]
  - porcentajeDiscografica  ∈ [0, 100]
  - estadoContrato IN ('Activo', 'Cancelado', 'Finalizado')
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

from usuarios.models import Artista
from .discografica import Discografica


class ContratoDiscografica(models.Model):
    ESTADO_CHOICES = [
        ('Activo',     'Activo'),
        ('Cancelado',  'Cancelado'),
        ('Finalizado', 'Finalizado'),
    ]

    id_contrato = models.AutoField(
        db_column='idContrato',
        primary_key=True,
    )
    artista = models.ForeignKey(
        Artista,
        db_column='Artista_idUsuario',
        on_delete=models.DO_NOTHING,
        related_name='contratos',
    )
    discografica = models.ForeignKey(
        Discografica,
        db_column='Discografica_idDiscografica',
        on_delete=models.DO_NOTHING,
        related_name='contratos',
    )
    fecha_inicio = models.DateField(
        db_column='fechaInicio',
    )
    fecha_fin = models.DateField(
        db_column='fechaFin',
        blank=True, null=True,
    )
    porcentaje_artista = models.DecimalField(
        db_column='porcentajeArtista',
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    porcentaje_discografica = models.DecimalField(
        db_column='porcentajeDiscografica',
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    estado_contrato = models.CharField(
        db_column='estadoContrato',
        max_length=20,
        choices=ESTADO_CHOICES,
        default='Activo',
    )

    class Meta:
        managed = False
        db_table = '[Industria].[ContratoDiscografica]'
        unique_together = (('artista', 'discografica', 'id_contrato'),)
        ordering = ['-fecha_inicio']
        verbose_name = 'Contrato con Discográfica'
        verbose_name_plural = 'Contratos con Discográficas'

    def __str__(self):
        return f'Contrato #{self.id_contrato} · {self.artista_id} ↔ {self.discografica_id}'

    def clean(self):
        super().clean()
        if self.fecha_fin and self.fecha_inicio and self.fecha_fin <= self.fecha_inicio:
            raise ValidationError({'fecha_fin': 'La fecha de fin debe ser mayor a la fecha de inicio.'})
        suma = (self.porcentaje_artista or 0) + (self.porcentaje_discografica or 0)
        if suma > 100:
            raise ValidationError('La suma de porcentajes no puede superar el 100%.')

    @property
    def es_activo(self) -> bool:
        return self.estado_contrato == 'Activo'
