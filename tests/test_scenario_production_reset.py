import datetime
import unittest
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from proteus import Model, Wizard
from trytond.modules.company.tests.tools import create_company
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):

        today = datetime.date.today()
        yesterday = today - relativedelta(days=1)
        yesterday - relativedelta(days=1)

        # Install production Module
        activate_modules(['production_reset', 'production_operation'])

        # Create company
        _ = create_company()

        # Create product
        ProductUom = Model.get('product.uom')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        ProductTemplate = Model.get('product.template')
        template = ProductTemplate()
        template.name = 'product'
        template.default_uom = unit
        template.type = 'goods'
        template.producible = True
        template.list_price = Decimal(30)
        product, = template.products
        product.cost_price = Decimal(20)
        template.save()
        product, = template.products

        # Create Components
        template1 = ProductTemplate()
        template1.name = 'component 1'
        template1.default_uom = unit
        template1.type = 'goods'
        template1.list_price = Decimal(5)
        component1, = template1.products
        component1.cost_price = Decimal(1)
        template1.save()
        component1, = template1.products
        meter, = ProductUom.find([('symbol', '=', 'm')])
        centimeter, = ProductUom.find([('symbol', '=', 'cm')])
        template2 = ProductTemplate()
        template2.name = 'component 2'
        template2.default_uom = meter
        template2.type = 'goods'
        template2.list_price = Decimal(7)
        component2, = template2.products
        component2.cost_price = Decimal(5)
        template2.save()
        component2, = template2.products

        # Create Bill of Material
        BOM = Model.get('production.bom')
        BOMInput = Model.get('production.bom.input')
        BOMOutput = Model.get('production.bom.output')
        bom = BOM(name='product')
        input1 = BOMInput()
        bom.inputs.append(input1)
        input1.product = component1
        input1.quantity = 5
        input2 = BOMInput()
        bom.inputs.append(input2)
        input2.product = component2
        input2.quantity = 150
        input2.unit = centimeter
        output = BOMOutput()
        bom.outputs.append(output)
        output.product = product
        output.quantity = 1
        bom.save()
        ProductBom = Model.get('product.product-production.bom')
        product.boms.append(ProductBom(bom=bom))
        product.save()
        ProductionLeadTime = Model.get('production.lead_time')
        production_lead_time = ProductionLeadTime()
        production_lead_time.product = product
        production_lead_time.bom = bom
        production_lead_time.lead_time = datetime.timedelta(1)
        production_lead_time.save()

        # Create an Inventory
        Inventory = Model.get('stock.inventory')
        InventoryLine = Model.get('stock.inventory.line')
        Location = Model.get('stock.location')
        storage, = Location.find([
            ('code', '=', 'STO'),
        ])
        inventory = Inventory()
        inventory.location = storage
        inventory_line1 = InventoryLine()
        inventory.lines.append(inventory_line1)
        inventory_line1.product = component1
        inventory_line1.quantity = 20
        inventory_line2 = InventoryLine()
        inventory.lines.append(inventory_line2)
        inventory_line2.product = component2
        inventory_line2.quantity = 6
        inventory.click('confirm')
        self.assertEqual(inventory.state, 'done')

        # Make a production
        Production = Model.get('production')
        production = Production()
        production.planned_date = today
        production.product = product
        production.bom = bom
        production.quantity = 2
        self.assertEqual(production.planned_start_date, yesterday)
        self.assertEqual(
            sorted([i.quantity for i in production.inputs]), [10, 300])
        output, = production.outputs
        self.assertEqual(output.quantity, 2)
        production.save()
        self.assertEqual(production.cost, Decimal('25.0000'))
        production.click('wait')
        self.assertEqual(production.state, 'waiting')

        # Do the production
        production.click('assign_try')
        self.assertEqual(all(i.state == 'assigned' for i in production.inputs),
                         True)
        production.click('run')
        self.assertEqual(all(i.state == 'done' for i in production.inputs),
                         True)
        self.assertEqual(
            len(set(i.effective_date == today for i in production.inputs)), 1)
        production.click('do')
        output, = production.outputs
        self.assertEqual(output.state, 'done')

        # Reset the production
        reset = Wizard('production.reset.wizard', [production])
        self.assertEqual(len(reset.form.moves),
                         len(production.inputs) + len(production.outputs))
        reset.form.name = 'Reset Production 1'
        reset.form.description = 'Reset Production 1'
        reset.execute('confirm')
        reset.execute('reset')
        self.assertEqual(production.state, 'draft')
        self.assertEqual(
            len([
                input for input in production.inputs
                if input.state == 'cancelled'
            ]), 2)
        self.assertEqual(
            len([
                input for input in production.inputs if input.state == 'draft'
            ]), 2)
        self.assertEqual(
            len([
                output for output in production.outputs
                if output.state == 'cancelled'
            ]), 1)
        self.assertEqual(
            len([
                output for output in production.outputs
                if output.state == 'draft'
            ]), 1)

        # Check production reset
        Reset = Model.get('production.reset')
        reset, = Reset.find([])
        self.assertEqual(len(reset.moves), 3)
