"""
Modelos de la app `industria` — esquema [Industria] de SQL Server.

Tablas:
  - [Industria].[Discografica]
  - [Industria].[ContratoDiscografica]
"""

from .discografica import Discografica
from .contrato_discografica import ContratoDiscografica

__all__ = ['Discografica', 'ContratoDiscografica']
