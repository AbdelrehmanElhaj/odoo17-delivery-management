import base64

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class DeliveryTrackingController(http.Controller):
    """Public routes — no authentication required."""

    @http.route(
        '/delivery/track/<string:token>',
        type='http',
        auth='public',
        website=False,
    )
    def track_delivery(self, token, **kw):
        order = request.env['delivery.order'].sudo().search(
            [('tracking_token', '=', token)], limit=1
        )
        if not order:
            return request.render('delivery_management.portal_tracking_not_found', {})

        vehicle = order.trip_id.vehicle_id if order.trip_id else None
        next_stop = order.next_stop_id
        stops_remaining = len(order.stop_ids.filtered(lambda s: s.status == 'pending'))

        return request.render('delivery_management.portal_tracking', {
            'order': order,
            'vehicle': vehicle,
            'next_stop': next_stop,
            'stops_remaining': stops_remaining,
        })

    @http.route(
        '/delivery/track/<string:token>/poll',
        type='json',
        auth='public',
    )
    def track_poll(self, token, **kw):
        """JSON endpoint polled every 60s by the tracking page JS."""
        order = request.env['delivery.order'].sudo().search(
            [('tracking_token', '=', token)], limit=1
        )
        if not order:
            return {'error': 'not_found'}

        vehicle = order.trip_id.vehicle_id if order.trip_id else None
        next_stop = order.next_stop_id
        stops_remaining = len(order.stop_ids.filtered(lambda s: s.status == 'pending'))

        return {
            'state': order.state,
            'lat': vehicle.last_lat if vehicle else None,
            'lng': vehicle.last_lng if vehicle else None,
            'gps_updated': vehicle.gps_updated.isoformat() if vehicle and vehicle.gps_updated else None,
            'eta': next_stop.eta.isoformat() if next_stop and next_stop.eta else None,
            'stops_remaining': stops_remaining,
        }


class DeliveryDriverPortal(CustomerPortal):
    """Authenticated portal routes for drivers."""

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'delivery_count' in counters:
            driver = request.env['delivery.driver'].sudo().search(
                [('user_id', '=', request.env.user.id)], limit=1
            )
            values['delivery_count'] = len(driver.current_trip_id) if driver else 0
        return values

    @http.route(
        '/my/deliveries',
        type='http',
        auth='user',
        website=False,
    )
    def portal_my_deliveries(self, **kw):
        driver = request.env['delivery.driver'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1
        )
        trips = request.env['delivery.trip'].browse()
        if driver:
            trips = request.env['delivery.trip'].sudo().search([
                ('driver_id', '=', driver.id),
                ('state', 'in', ['dispatched', 'in_progress']),
            ])
        return request.render('delivery_management.portal_my_deliveries', {
            'trips': trips,
            'driver': driver,
        })

    @http.route(
        '/my/stop/<int:stop_id>/arrive',
        type='http',
        auth='user',
        website=False,
    )
    def stop_arrive(self, stop_id, **kw):
        stop = self._get_driver_stop(stop_id)
        if stop:
            stop.sudo().action_arrive()
        return request.redirect('/my/deliveries')

    @http.route(
        '/my/stop/<int:stop_id>/done',
        type='http',
        auth='user',
        website=False,
    )
    def stop_done(self, stop_id, **kw):
        stop = self._get_driver_stop(stop_id)
        if stop:
            stop.sudo().action_done()
        return request.redirect('/my/deliveries')

    @http.route(
        '/my/stop/<int:stop_id>/failed',
        type='http',
        auth='user',
        website=False,
    )
    def stop_failed(self, stop_id, **kw):
        stop = self._get_driver_stop(stop_id)
        if stop:
            stop.sudo().action_failed()
        return request.redirect('/my/deliveries')

    @http.route(
        '/my/stop/<int:stop_id>/photo',
        type='http',
        auth='user',
        methods=['POST'],
        website=False,
        csrf=True,
    )
    def stop_photo(self, stop_id, photo=None, **kw):
        stop = self._get_driver_stop(stop_id)
        if stop and photo:
            image_data = base64.b64encode(photo.read())
            request.env['delivery.photo'].sudo().create({
                'stop_id': stop.id,
                'image': image_data,
                'taken_by': request.env.user.id,
            })
        return request.redirect('/my/deliveries')

    def _get_driver_stop(self, stop_id):
        """Return the stop only if it belongs to a trip assigned to the current driver."""
        driver = request.env['delivery.driver'].sudo().search(
            [('user_id', '=', request.env.user.id)], limit=1
        )
        if not driver:
            return None
        stop = request.env['delivery.stop'].sudo().browse(stop_id)
        if stop.exists() and stop.trip_id.driver_id == driver:
            return stop
        return None
