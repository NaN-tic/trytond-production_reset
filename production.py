from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import  PoolMeta
from trytond.pyson import Eval, Id

__all__ = ['Production']


class Production(metaclass=PoolMeta):
    __name__ = 'production'

    @classmethod
    def __setup__(cls):
        super(Production, cls).__setup__()
        cls._buttons.update({
                'reset_wizard': {
                    'invisible': ~Id('stock',
                        'group_stock_force_assignment').in_(
                        Eval('context', {}).get('groups', [])) | ~Eval(
                            'state').in_(['running', 'done']),
                    'depends': ['state'],
                    },
                })

    @classmethod
    @ModelView.button_action('production_reset.act_production_reset_wizard')
    def reset_wizard(cls, productions):
        pass
