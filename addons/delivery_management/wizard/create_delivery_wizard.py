from odoo import api, fields, models


class CreateDeliveryWizard(models.TransientModel):
    _name = 'create.delivery.wizard'
    _description = 'Create Delivery Order from Sales Order'

    sale_order_id = fields.Many2one(
        'sale.order', string='Sales Order', readonly=True, required=True,
    )
    partner_id = fields.Many2one(
        'res.partner', string='Delivery Address', required=True,
    )
    mode = fields.Selection(
        [('pickup', 'Pickup'), ('delivery', 'Delivery')],
        string='Mode',
        required=True,
        default='delivery',
    )
    scheduled_date = fields.Datetime(string='Scheduled Date')
    notes = fields.Text(string='Notes')

    @api.onchange('sale_order_id')
    def _onchange_sale_order_id(self):
        if self.sale_order_id:
            self.partner_id = (
                self.sale_order_id.partner_shipping_id
                or self.sale_order_id.partner_id
            )

    def action_create(self):
        self.ensure_one()
        order = self.env['delivery.order'].create({
            'sale_order_id': self.sale_order_id.id,
            'partner_id': self.partner_id.id,
            'mode': self.mode,
            'scheduled_date': self.scheduled_date,
            'notes': self.notes,
            'state': 'confirmed',
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Delivery Order',
            'res_model': 'delivery.order',
            'res_id': order.id,
            'view_mode': 'form',
            'target': 'current',
        }
