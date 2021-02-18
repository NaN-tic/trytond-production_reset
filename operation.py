from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import  PoolMeta

__all__ = ['Operation']


class Operation(metaclass=PoolMeta):
    __name__ = 'production.operation'
    production_reset = fields.Many2One('production.reset', 'Production Reset')
