import urllib.request
import json as _json
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class DeliveryTrip(models.Model):
    _name = 'delivery.trip'
    _description = 'Delivery Trip'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'scheduled_date desc, id desc'

    name = fields.Char(
        string='Trip Reference', default='New', readonly=True, copy=False, tracking=True,
    )
    vehicle_id = fields.Many2one(
        'delivery.vehicle', string='Vehicle', required=True, tracking=True,
    )
    driver_id = fields.Many2one(
        'delivery.driver', string='Driver', required=True, tracking=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('dispatched', 'Dispatched'),
            ('in_progress', 'In Progress'),
            ('done', 'Done'),
            ('cancelled', 'Cancelled'),
        ],
        default='draft',
        tracking=True,
        string='Status',
    )
    scheduled_date = fields.Datetime(string='Scheduled Date', tracking=True)
    actual_start = fields.Datetime(string='Actual Start', tracking=True)
    actual_end = fields.Datetime(string='Actual End', tracking=True)

    order_ids = fields.One2many('delivery.order', 'trip_id', string='Delivery Orders')
    stop_ids = fields.One2many('delivery.stop', 'trip_id', string='Stops')

    order_count = fields.Integer(compute='_compute_counts', string='Orders')
    stop_count = fields.Integer(compute='_compute_counts', string='Stops')
    pending_stop_count = fields.Integer(compute='_compute_counts', string='Pending Stops')

    notes = fields.Text()

    # ── Computed ──────────────────────────────────────────────────────────

    @api.depends('order_ids', 'stop_ids', 'stop_ids.status')
    def _compute_counts(self):
        for trip in self:
            trip.order_count = len(trip.order_ids)
            trip.stop_count = len(trip.stop_ids)
            trip.pending_stop_count = len(trip.stop_ids.filtered(lambda s: s.status == 'pending'))

    # ── ORM hooks ─────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('delivery.trip') or 'New'
        return super().create(vals_list)

    # ── State transitions ─────────────────────────────────────────────────

    def action_dispatch(self):
        for trip in self:
            if not trip.stop_ids:
                raise UserError(f'Trip {trip.name} has no stops. Add at least one stop before dispatching.')
        self.write({'state': 'dispatched'})
        for trip in self:
            trip.order_ids.filtered(lambda o: o.state == 'draft').action_confirm()

    def action_start(self):
        self.write({'state': 'in_progress', 'actual_start': fields.Datetime.now()})
        for trip in self:
            trip.order_ids.filtered(
                lambda o: o.state in ['draft', 'confirmed']
            ).write({'state': 'in_progress'})

    def action_done(self):
        self.write({'state': 'done', 'actual_end': fields.Datetime.now()})
        for trip in self:
            trip.order_ids.filtered(lambda o: o.state == 'in_progress').action_done()

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft', 'actual_start': False, 'actual_end': False})

    # ── Smart button helpers ───────────────────────────────────────────────

    def action_view_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Delivery Orders',
            'res_model': 'delivery.order',
            'view_mode': 'tree,form',
            'domain': [('trip_id', '=', self.id)],
        }

    # ── ETA cron ──────────────────────────────────────────────────────────

    @api.model
    def _cron_update_etas(self):
        """Refresh ETAs using OSRM public routing API for all in-progress trips."""
        trips = self.search([('state', '=', 'in_progress')])
        for trip in trips:
            vehicle = trip.vehicle_id
            if not (vehicle.last_lat and vehicle.last_lng):
                continue
            # Chain ETAs: start from the vehicle's current position
            cur_lat = vehicle.last_lat
            cur_lng = vehicle.last_lng
            for stop in trip.stop_ids.filtered(lambda s: s.status == 'pending').sorted('sequence'):
                if not (stop.partner_lat and stop.partner_lng):
                    continue
                duration = self._osrm_duration(cur_lat, cur_lng, stop.partner_lat, stop.partner_lng)
                if duration is not None:
                    eta = fields.Datetime.now() + timedelta(seconds=duration)
                    stop.write({'eta': eta})
                cur_lat = stop.partner_lat
                cur_lng = stop.partner_lng

    @api.model
    def _osrm_duration(self, from_lat, from_lng, to_lat, to_lng):
        """Return drive-time in seconds from OSRM, or None on error."""
        url = (
            f"http://router.project-osrm.org/route/v1/driving/"
            f"{from_lng},{from_lat};{to_lng},{to_lat}"
            f"?overview=false"
        )
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = _json.loads(resp.read())
            routes = data.get('routes', [])
            if routes:
                return routes[0]['duration']
        except Exception:
            pass
        return None
