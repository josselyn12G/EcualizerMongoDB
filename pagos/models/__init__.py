"""
Modelos de la app `pagos` — esquema [Pagos] de SQL Server.

Tablas:
  - [Pagos].[TipoPlan]    → modelo TipoPlan    (catálogo de planes)
  - [Pagos].[Suscripcion] → modelo Suscripcion (Usuario ↔ TipoPlan)
  - [Pagos].[Pago]        → modelo Pago        (transacciones)

"Plan" del usuario = TipoPlan asociado vía Suscripcion vigente
(estado='activa' AND fechaFin >= hoy).
"""

from .tipo_plan import TipoPlan
from .suscripcion import Suscripcion
from .pago import Pago

__all__ = ['TipoPlan', 'Suscripcion', 'Pago']
