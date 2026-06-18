"""
Modelo Pago — refleja [Pagos].[Pago]

Cada cobro contra una Suscripcion. CHECKs:
  - monto > 0
  - metodoPago    IN ('Paypal', 'Tarjeta de credito', 'Tarjeta de debito')
  - resultadoPago IN ('Completado', 'Fallido', 'Pendiente', 'Reembolsado')
"""

from django.db import models
from django.core.validators import MinValueValidator

from .suscripcion import Suscripcion


class Pago(models.Model):
    METODO_CHOICES = [
        ('Paypal',              'PayPal'),
        ('Tarjeta de credito',  'Tarjeta de crédito'),
        ('Tarjeta de debito',   'Tarjeta de débito'),
    ]
    RESULTADO_CHOICES = [
        ('Completado',  'Completado'),
        ('Fallido',     'Fallido'),
        ('Pendiente',   'Pendiente'),
        ('Reembolsado', 'Reembolsado'),
    ]

    id_pago = models.AutoField(
        db_column='idPago',
        primary_key=True,
    )
    fecha_pago = models.DateTimeField(
        db_column='fechaPago',
        auto_now_add=True,
    )
    monto = models.DecimalField(
        db_column='monto',
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )
    metodo_pago = models.CharField(
        db_column='metodoPago',
        max_length=50,
        choices=METODO_CHOICES,
    )
    resultado_pago = models.CharField(
        db_column='resultadoPago',
        max_length=20,
        choices=RESULTADO_CHOICES,
        default='Pendiente',
    )
    suscripcion = models.ForeignKey(
        Suscripcion,
        db_column='Suscripcion_idSuscripcion',
        on_delete=models.DO_NOTHING,
        related_name='pagos',
    )

    class Meta:
        managed = False
        db_table = '[Pagos].[Pago]'
        ordering = ['-fecha_pago']

    def __str__(self):
        return f'Pago #{self.id_pago} · ${self.monto} · {self.resultado_pago}'

    @property
    def es_exitoso(self) -> bool:
        return self.resultado_pago == 'Completado'
