from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.transaction import Transaction

__all__ = ['ProductionReset', 'ProductionResetWizardStart', 'ProductionResetWizard']


class ProductionReset(ModelSQL, ModelView):
    '''Production Reset'''
    __name__ = 'production.reset'
    request_date = fields.Date('Request Date', required=True)
    name = fields.Char('Reason', required=True)
    description = fields.Char('Description', required=True)
    moves = fields.One2Many('stock.move', 'origin', 'Moves')

    @classmethod
    def __setup__(cls):
        super(ProductionReset, cls).__setup__()
        try:
            Operation = Pool().get('production.operation')
            cls.operations = fields.One2Many('production.operation',
                'production_reset', 'Operations')
        except KeyError:
            pass
        cls._order = [
            ('request_date', 'DESC'),
            ('id', 'DESC'),
            ]

class ProductionResetWizardStart(ModelView):
    'Production Reset Start'
    __name__ = 'production.reset.wizard.start'
    name = fields.Char('Reason', required=True)
    description = fields.Char('Description', required=True)
    moves = fields.One2Many('stock.move', None, 'Moves', readonly=True)

    @classmethod
    def __setup__(cls):
        super(ProductionResetWizardStart, cls).__setup__()
        try:
            Operation = Pool().get('production.operation')
            cls.operations = fields.One2Many('production.operation',
                None, 'Operations')
        except KeyError:
            pass


class ProductionResetWizard(Wizard):
    'Production Reset Wizard'
    __name__ = "production.reset.wizard"

    start = StateView('production.reset.wizard.start',
        'production_reset.production_reset_start', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Reset', 'reset', 'tryton-ok', default=True),
            ])
    reset = StateTransition()

    def transition_reset(self):
        pool = Pool()
        Production = pool.get('production')
        Move = pool.get('stock.move')
        Reset = pool.get('production.reset')
        Date_ = pool.get('ir.date')

        try:
            Operation = Pool().get('production.operation')
            operation_h = Operation.__table__()
        except KeyError:
            Operation, operation_h = None, None

        production_h = Production.__table__()
        move_h = Move.__table__()
        today = Date_.today()
        cursor = Transaction().connection.cursor()

        production_ids = Transaction().context['active_ids']
        move_ids = [m.id for m in self.start.moves]
        if Operation:
            operation_ids = [m.id for m in self.start.operations]
        else:
            operation_ids = []

        # if not moves and not operatons, end
        if not move_ids and not operation_ids:
            return 'end'

        reset = Reset()
        reset.name = self.start.name
        reset.description = self.start.description
        reset.request_date = today
        reset.save()

        # reset moves
        if move_ids:
            Move.copy(self.start.moves)
            sql_where = (move_h.id.in_(move_ids))
            cursor.execute(*move_h.update(
                columns=[move_h.state, move_h.origin],
                values=['cancel', '%s,%s' % (Reset.__name__, reset.id)],
                where=sql_where))

        # reset operations
        if operation_ids:
            Operation.copy(self.start.operations)
            sql_where = (operation_h.id.in_(operation_ids))
            cursor.execute(*operation_h.update(
                columns=[operation_h.production_reset],
                values=[reset.id],
                where=sql_where))

        if move_ids or operation_ids:
            sql_where = (production_h.id.in_(production_ids))
            cursor.execute(*production_h.update(
                columns=[production_h.state],
                values=['draft'],
                where=sql_where))

        return 'end'

    def default_start(self, fields):
        Production = Pool().get('production')
        production = Production(Transaction().context['active_id'])

        defaults = {
            'moves': ([m.id for m in production.inputs if m.state in ('assigned', 'done')]
                + [m.id for m in production.outputs if m.state in ('assigned', 'done')]),
            }
        if hasattr(production, 'operations'):
            # TODO filter operations by state ?
            defaults['operations'] = [o.id for o in production.operations]
        return defaults
