from odoo import api, fields, models


class DeliveryVehicle(models.Model):
    _name = 'delivery.vehicle'
    _description = 'Delivery Vehicle'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    plate = fields.Char(string='License Plate', required=True, tracking=True)
    capacity = fields.Float(string='Capacity (kg)', tracking=True)
    active = fields.Boolean(default=True, tracking=True)

    traccar_device_id = fields.Char(
        string='Traccar Device ID',
        index=True,
        help='Matches the identifier configured in the Traccar driver app.',
    )
    last_lat = fields.Float(string='Latitude', digits=(10, 7), readonly=True)
    last_lng = fields.Float(string='Longitude', digits=(10, 7), readonly=True)
    gps_updated = fields.Datetime(string='GPS Last Updated', readonly=True)

    driver_ids = fields.One2many('delivery.driver', 'vehicle_id', string='Drivers')
    driver_count = fields.Integer(compute='_compute_driver_count', string='Drivers')

    active_trip_id = fields.Many2one(
        'delivery.trip',
        compute='_compute_active_trip',
        string='Active Trip',
        store=False,
    )

    @api.depends('driver_ids')
    def _compute_driver_count(self):
        for v in self:
            v.driver_count = len(v.driver_ids)

    def _compute_active_trip(self):
        for v in self:
            trip = self.env['delivery.trip'].search(
                [('vehicle_id', '=', v.id), ('state', 'in', ['dispatched', 'in_progress'])],
                limit=1,
            )
            v.active_trip_id = trip

    def action_view_drivers(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Drivers',
            'res_model': 'delivery.driver',
            'view_mode': 'tree,form',
            'domain': [('vehicle_id', '=', self.id)],
            'context': {'default_vehicle_id': self.id},
        }

    @api.model
    def update_gps_position(self, device_id, lat, lng):
        """Called by the Traccar bridge via JSON-RPC to update vehicle position."""
        vehicle = self.search([('traccar_device_id', '=', device_id)], limit=1)
        if vehicle:
            vehicle.write({
                'last_lat': lat,
                'last_lng': lng,
                'gps_updated': fields.Datetime.now(),
            })
            return {'success': True, 'vehicle_id': vehicle.id}
        return {'success': False, 'error': f'No vehicle with device_id={device_id}'}
