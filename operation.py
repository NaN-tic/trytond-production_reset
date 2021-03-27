from trytond.model import fields
from trytond.pool import  PoolMeta


class Operation(metaclass=PoolMeta):
    __name__ = 'production.operation'
    production_reset = fields.Many2One('production.reset', 'Production Reset')
