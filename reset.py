from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import Pool
from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.transaction import Transaction
from trytond.pyson import Bool, Eval


class ProductionReset(ModelSQL, ModelView):
    '''Production Reset'''
    __name__ = 'production.reset'
    production = fields.Many2One('production', 'Production', required=True)
    request_date = fields.Date('Request Date', required=True)
    name = fields.Char('Reason', required=True)
    description = fields.Char('Description', required=True)
    moves = fields.One2Many('stock.move', 'origin', 'Moves')

    @classmethod
    def __setup__(cls):
        super(ProductionReset, cls).__setup__()
        try:
            Pool().get('production.operation')
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
    name = fields.Char('Reason', required=True, states={
            'readonly': Eval('confirmed', True),
        }, depends=['confirmed'])
    description = fields.Text('Description', required=True, states={
            'readonly': Eval('confirmed', True),
        }, depends=['confirmed'])
    moves = fields.One2Many('stock.move', None, 'Moves', readonly=True)
    confirmed = fields.Boolean('Confirmed', readonly=True)

    @classmethod
    def __setup__(cls):
        super(ProductionResetWizardStart, cls).__setup__()
        try:
            Pool().get('production.operation')
            cls.operations = fields.One2Many('production.operation',
                None, 'Operations', readonly=True)
        except KeyError:
            pass

    @classmethod
    def view_attributes(cls):
        states = {'invisible': ~Bool(Eval('confirmed'))}
        return [
            ('/form/group[@id="icon"]/image[@name="tryton-info"]', 'states', states),
            ('/form/group[@id="labels"]/label[@id="confirm"]', 'states', states),
            ]


class ProductionResetWizard(Wizard):
    'Production Reset Wizard'
    __name__ = "production.reset.wizard"

    start = StateView('production.reset.wizard.start',
        'production_reset.production_reset_start', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Confirm', 'confirm', 'tryton-ok', default=True),
            ])
    confirm = StateView('production.reset.wizard.start',
        'production_reset.production_reset_start', [
            Button('Cancel', 'end', 'tryton-cancel', default=True),
            Button('Reset', 'reset', 'tryton-ok'),
            ])
    reset = StateTransition()

    def default_start(self, fields):
        Production = Pool().get('production')
        production = Production(Transaction().context['active_id'])

        defaults = {
            'moves': ([m.id for m in production.inputs if m.state == 'done']
                + [m.id for m in production.outputs if m.state == 'done']),
            }
        if hasattr(production, 'operations'):
            defaults['operations'] = [o.id for o in production.operations
                if o.state == 'done']
        return defaults

    def default_confirm(self, fields):
        Production = Pool().get('production')
        production = Production(Transaction().context['active_id'])

        defaults = {
            'confirmed': True,
            'name': self.start.name,
            'description': self.start.description,
            'moves': [m.id for m in self.start.moves],
            }
        if hasattr(production, 'operations'):
            defaults['operations'] = [o.id for o in self.start.operations]
        return defaults

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

        production = Production(Transaction().context['active_id'])
        move_ids = [m.id for m in self.confirm.moves]
        if Operation:
            operation_ids = [m.id for m in self.confirm.operations]
        else:
            operation_ids = []

        # if not moves and not operatons, end
        if not move_ids and not operation_ids:
            return 'end'

        # TODO stock.period to allow reset moves

        reset = Reset()
        reset.production = production
        reset.name = self.confirm.name
        reset.description = self.confirm.description
        reset.request_date = today
        reset.save()

        if move_ids or operation_ids:
            sql_where = (production_h.id.in_([production.id]))
            cursor.execute(*production_h.update(
                columns=[production_h.state],
                values=['draft'],
                where=sql_where))

        # reset moves
        if move_ids:
            Move.copy(self.confirm.moves)
            sql_where = (move_h.id.in_(move_ids))
            cursor.execute(*move_h.update(
                columns=[move_h.state, move_h.origin],
                values=['cancelled', '%s,%s' % (Reset.__name__, reset.id)],
                where=sql_where))

        # reset operations
        if operation_ids:
            Operation.copy(self.confirm.operations)
            sql_where = (operation_h.id.in_(operation_ids))
            cursor.execute(*operation_h.update(
                columns=[operation_h.state, operation_h.production_reset],
                values=['cancelled', reset.id],
                where=sql_where))

        return 'end'
