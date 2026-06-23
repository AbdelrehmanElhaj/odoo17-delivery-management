from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_order_ids = fields.One2many(
        'delivery.order', 'sale_order_id', string='Delivery Orders',
    )
    delivery_count = fields.Integer(
        compute='_compute_delivery_count', string='Deliveries',
    )

    @api.depends('delivery_order_ids')
    def _compute_delivery_count(self):
        for order in self:
            order.delivery_count = len(order.delivery_order_ids)

    def action_create_delivery(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Delivery Order',
            'res_model': 'create.delivery.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_order_id': self.id,
                'default_partner_id': self.partner_shipping_id.id or self.partner_id.id,
            },
        }

    def action_view_deliveries(self):
        self.ensure_one()
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Delivery Orders',
            'res_model': 'delivery.order',
            'domain': [('sale_order_id', '=', self.id)],
        }
        if self.delivery_count == 1:
            action.update({'view_mode': 'form', 'res_id': self.delivery_order_ids[0].id})
        else:
            action['view_mode'] = 'tree,form'
        return action
