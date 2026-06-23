from odoo import fields, models


class DeliveryPhoto(models.Model):
    _name = 'delivery.photo'
    _description = 'Delivery Photo (Proof of Delivery)'
    _order = 'taken_at desc, id desc'

    stop_id = fields.Many2one(
        'delivery.stop', string='Stop', required=True, ondelete='cascade', index=True,
    )
    order_id = fields.Many2one(
        'delivery.order', related='stop_id.order_id', store=True, string='Order', index=True,
    )
    trip_id = fields.Many2one(
        'delivery.trip', related='stop_id.trip_id', store=True, string='Trip', index=True,
    )

    image = fields.Image(
        string='Photo', max_width=1920, max_height=1920, required=True,
    )
    taken_at = fields.Datetime(string='Taken At', default=fields.Datetime.now)
    taken_by = fields.Many2one(
        'res.users', string='Taken By', default=lambda self: self.env.user,
    )
    notes = fields.Text(string='Notes')
