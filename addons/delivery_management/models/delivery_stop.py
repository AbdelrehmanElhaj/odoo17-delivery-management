from odoo import api, fields, models


class DeliveryStop(models.Model):
    _name = 'delivery.stop'
    _description = 'Delivery Stop'
    _order = 'trip_id, sequence, id'

    trip_id = fields.Many2one(
        'delivery.trip', string='Trip', required=True, ondelete='cascade', index=True,
    )
    order_id = fields.Many2one(
        'delivery.order', string='Delivery Order', ondelete='set null', index=True,
    )
    sequence = fields.Integer(default=10)

    partner_id = fields.Many2one('res.partner', string='Delivery Address', required=True)
    partner_lat = fields.Float(string='Latitude', digits=(10, 7))
    partner_lng = fields.Float(string='Longitude', digits=(10, 7))

    status = fields.Selection(
        [
            ('pending', 'Pending'),
            ('arrived', 'Arrived'),
            ('done', 'Done'),
            ('failed', 'Failed'),
        ],
        default='pending',
        string='Status',
    )
    eta = fields.Datetime(string='ETA')
    actual_arrival = fields.Datetime(string='Actual Arrival')
    notes = fields.Text()

    photo_ids = fields.One2many('delivery.photo', 'stop_id', string='Photos')
    photo_count = fields.Integer(compute='_compute_photo_count', string='Photos')

    # ── Computed ──────────────────────────────────────────────────────────

    @api.depends('photo_ids')
    def _compute_photo_count(self):
        for stop in self:
            stop.photo_count = len(stop.photo_ids)

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.partner_id:
            self.partner_lat = self.partner_id.partner_latitude or 0.0
            self.partner_lng = self.partner_id.partner_longitude or 0.0

    # ── State transitions ─────────────────────────────────────────────────

    def action_arrive(self):
        self.write({'status': 'arrived', 'actual_arrival': fields.Datetime.now()})

    def action_done(self):
        self.write({'status': 'done'})
        for stop in self:
            if stop.order_id:
                pending = stop.order_id.stop_ids.filtered(
                    lambda s: s.status not in ['done', 'failed']
                )
                if not pending:
                    stop.order_id.action_done()

    def action_failed(self):
        self.write({'status': 'failed'})
        for stop in self:
            if stop.order_id:
                stop.order_id.action_failed()

    def action_reset_pending(self):
        self.write({'status': 'pending', 'actual_arrival': False})
