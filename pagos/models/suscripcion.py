"""
Modelo Suscripcion — refleja [Pagos].[Suscripcion]

Es el VÍNCULO entre un Usuario y un TipoPlan. El "plan" de un usuario
es el TipoPlan asociado a su suscripción VIGENTE (estado='activa' y
fechaFin >= hoy).

CHECKs:
  - estadoSuscripcion IN ('activa', 'cancelada', 'inactiva')
  - renovacionAutomatica IN ('S', 'N')
"""

from datetime import date
from django.db import models
from django.core.exceptions import ValidationError

from usuarios.models import Usuario
from .tipo_plan import TipoPlan


class Suscripcion(models.Model):
    ESTADO_CHOICES = [
        ('activa',    'Activa'),
        ('cancelada', 'Cancelada'),
        ('inactiva',  'Inactiva'),
    ]
    FLAG_CHOICES = [('S', 'Sí'), ('N', 'No')]

    id_suscripcion = models.AutoField(
        db_column='idSuscripcion',
        primary_key=True,
    )
    fecha_inicio = models.DateField(db_column='fechaInicio')
    fecha_fin    = models.DateField(db_column='fechaFin')
    estado_suscripcion = models.CharField(
        db_column='estadoSuscripcion',
        max_length=20,
        choices=ESTADO_CHOICES,
        default='activa',
    )
    renovacion_automatica = models.CharField(
        db_column='renovacionAutomatica',
        max_length=1,
        choices=FLAG_CHOICES,
        default='S',
    )
    usuario = models.ForeignKey(
        Usuario,
        db_column='Usuario_idUsuario',
        on_delete=models.DO_NOTHING,
        related_name='suscripciones',
    )
    tipo_plan = models.ForeignKey(
        TipoPlan,
        db_column='TipoPlan_idTipoPlan',
        on_delete=models.DO_NOTHING,
        related_name='suscripciones',
    )

    class Meta:
        managed = False
        db_table = '[Pagos].[Suscripcion]'
        ordering = ['-fecha_inicio']
        verbose_name = 'Suscripción'
        verbose_name_plural = 'Suscripciones'

    def __str__(self):
        return f'Suscripción #{self.id_suscripcion} · {self.tipo_plan_id} → {self.usuario_id}'

    def clean(self):
        super().clean()
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin <= self.fecha_inicio:
            raise ValidationError({'fecha_fin': 'La fecha de fin debe ser posterior a la de inicio.'})

    # ── Helpers semánticos ──
    @property
    def es_vigente(self) -> bool:
        return self.estado_suscripcion == 'activa' and self.fecha_fin >= date.today()

    @property
    def es_vencida(self) -> bool:
        return self.estado_suscripcion == 'activa' and self.fecha_fin < date.today()

    @property
    def estado_efectivo(self) -> str:
        if self.es_vigente:  return 'Vigente'
        if self.es_vencida:  return 'Vencida'
        return self.get_estado_suscripcion_display()
