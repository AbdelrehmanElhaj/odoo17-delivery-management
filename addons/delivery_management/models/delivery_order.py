import secrets

from odoo import api, fields, models
from odoo.exceptions import UserError


class DeliveryOrder(models.Model):
    _name = 'delivery.order'
    _description = 'Delivery Order'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'scheduled_date desc, id desc'

    name = fields.Char(
        string='Reference', default='New', readonly=True, copy=False, tracking=True,
    )
    sale_order_id = fields.Many2one('sale.order', string='Sales Order', tracking=True, ondelete='set null')
    mode = fields.Selection(
        [('pickup', 'Pickup'), ('delivery', 'Delivery')],
        required=True,
        default='delivery',
        tracking=True,
    )
    partner_id = fields.Many2one('res.partner', string='Customer', required=True, tracking=True)
    partner_lat = fields.Float(string='Latitude', digits=(10, 7))
    partner_lng = fields.Float(string='Longitude', digits=(10, 7))
    scheduled_date = fields.Datetime(string='Scheduled Date', tracking=True)

    trip_id = fields.Many2one(
        'delivery.trip', string='Trip', tracking=True, ondelete='set null',
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('confirmed', 'Confirmed'),
            ('in_progress', 'In Progress'),
            ('done', 'Done'),
            ('failed', 'Failed'),
        ],
        default='draft',
        tracking=True,
        string='Status',
    )
    tracking_token = fields.Char(
        string='Tracking Token', readonly=True, copy=False, index=True,
    )
    portal_url = fields.Char(string='Tracking URL', compute='_compute_portal_url', store=False)

    stop_ids = fields.One2many('delivery.stop', 'order_id', string='Stops')
    stop_count = fields.Integer(compute='_compute_stop_count', string='Stops')
    next_stop_id = fields.Many2one(
        'delivery.stop', string='Next Stop', compute='_compute_next_stop', store=False,
    )
    notes = fields.Text()

    # ── Computed fields ───────────────────────────────────────────────────

    def _compute_portal_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for order in self:
            if order.tracking_token:
                order.portal_url = f"{base_url}/delivery/track/{order.tracking_token}"
            else:
                order.portal_url = False

    def _compute_access_url(self):
        for order in self:
            order.access_url = f'/delivery/track/{order.tracking_token}' if order.tracking_token else '/'

    def _compute_stop_count(self):
        for order in self:
            order.stop_count = len(order.stop_ids)

    def _compute_next_stop(self):
        for order in self:
            stop = self.env['delivery.stop'].search(
                [('order_id', '=', order.id), ('status', '=', 'pending')],
                order='sequence asc',
                limit=1,
            )
            order.next_stop_id = stop

    # ── ORM hooks ─────────────────────────────────────────────────────────

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('delivery.order') or 'New'
            if not vals.get('tracking_token'):
                vals['tracking_token'] = secrets.token_urlsafe(16)
        return super().create(vals_list)

    # ── State transitions ─────────────────────────────────────────────────

    def action_confirm(self):
        for order in self:
            if order.state != 'draft':
                raise UserError(f'{order.name} is not in Draft state.')
        self.write({'state': 'confirmed'})
        template = self.env.ref(
            'delivery_management.mail_template_delivery_tracking',
            raise_if_not_found=False,
        )
        if template:
            for order in self:
                if order.partner_id.email:
                    template.sudo().send_mail(order.id, force_send=True)

    def action_in_progress(self):
        self.write({'state': 'in_progress'})

    def action_done(self):
        self.write({'state': 'done'})

    def action_failed(self):
        self.write({'state': 'failed'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    # ── Smart button helpers ───────────────────────────────────────────────

    def action_open_trip(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'delivery.trip',
            'res_id': self.trip_id.id,
            'view_mode': 'form',
        }

    def action_open_tracking_url(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.portal_url,
            'target': 'new',
        }
