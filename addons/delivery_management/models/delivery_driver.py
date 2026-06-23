from odoo import api, fields, models


class DeliveryDriver(models.Model):
    _name = 'delivery.driver'
    _description = 'Delivery Driver'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    user_id = fields.Many2one(
        'res.users',
        string='Portal User',
        tracking=True,
        help='Odoo portal user this driver logs in as.',
    )
    vehicle_id = fields.Many2one('delivery.vehicle', string='Default Vehicle', tracking=True)
    phone = fields.Char(tracking=True)
    active = fields.Boolean(default=True, tracking=True)

    current_trip_id = fields.Many2one(
        'delivery.trip',
        string='Active Trip',
        compute='_compute_current_trip',
        store=False,
    )

    def _compute_current_trip(self):
        for driver in self:
            trip = self.env['delivery.trip'].search(
                [('driver_id', '=', driver.id), ('state', 'in', ['dispatched', 'in_progress'])],
                limit=1,
            )
            driver.current_trip_id = trip
