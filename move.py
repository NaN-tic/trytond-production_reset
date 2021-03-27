from trytond.pool import  PoolMeta


class Move(metaclass=PoolMeta):
    __name__ = 'stock.move'
    # production_reset = fields.Many2One('production.reset', 'Production Reset')

    @classmethod
    def _get_origin(cls):
        return super(Move, cls)._get_origin() + ['production.reset']
