"""
Modelo TipoPlan — refleja [Pagos].[TipoPlan]

Catálogo de planes disponibles (Free, Premium Mensual, Premium Anual, etc.).
CHECKs:
  - precio >= 0
  - duracion IN ('Anual', 'Mensual')
  - nombrePlan UNIQUE
"""

from django.db import models
from django.core.validators import MinValueValidator


class TipoPlan(models.Model):
    DURACION_CHOICES = [('Mensual', 'Mensual'), ('Anual', 'Anual')]

    id_tipo_plan = models.AutoField(
        db_column='idTipoPlan',
        primary_key=True,
    )
    nombre_plan = models.CharField(
        db_column='nombrePlan',
        max_length=40,
        unique=True,
    )
    descripcion_plan = models.TextField(
        db_column='descripcionPlan',
        blank=True, null=True,
    )
    precio = models.DecimalField(
        db_column='precio',
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    duracion = models.CharField(
        db_column='duracion',
        max_length=20,
        choices=DURACION_CHOICES,
    )

    class Meta:
        managed = False
        db_table = '[Pagos].[TipoPlan]'
        ordering = ['precio', 'nombre_plan']
        verbose_name = 'Tipo de plan'
        verbose_name_plural = 'Tipos de plan'

    def __str__(self):
        return f'{self.nombre_plan} ({self.duracion})'

    @property
    def es_free(self) -> bool:
        return 'free' in (self.nombre_plan or '').lower()
