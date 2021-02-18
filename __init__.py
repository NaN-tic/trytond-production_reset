# This file is part production_reset module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from . import reset
from . import move
from . import operation
from . import production

def register():
    Pool.register(
        reset.ProductionReset,
        reset.ProductionResetWizardStart,
        move.Move,
        production.Production,
        module='production_reset', type_='model')
    Pool.register(
        reset.ProductionResetWizard,
        module='production_reset', type_='wizard')
    Pool.register(
        operation.Operation,
        depends=['production_operation'],
        module='production_reset', type_='model')
