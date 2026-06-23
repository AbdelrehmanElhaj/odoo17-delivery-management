from odoo import http
from odoo.http import request


class DeliveryDashboardController(http.Controller):

    @http.route('/delivery/dashboard/data', type='json', auth='user')
    def dashboard_data(self, **kw):
        if not request.env.user.has_group('delivery_management.group_delivery_manager'):
            return {'error': 'access_denied'}

        vehicles = request.env['delivery.vehicle'].sudo().search([('active', '=', True)])
        active_trips = request.env['delivery.trip'].sudo().search([
            ('state', 'in', ['dispatched', 'in_progress'])
        ])

        trip_by_vehicle = {}
        for t in active_trips:
            trip_by_vehicle[t.vehicle_id.id] = t

        vehicle_data = []
        for v in vehicles:
            trip = trip_by_vehicle.get(v.id)
            vehicle_data.append({
                'id': v.id,
                'name': v.name,
                'plate': v.plate,
                'lat': v.last_lat if v.last_lat else None,
                'lng': v.last_lng if v.last_lng else None,
                'gps_updated': v.gps_updated.strftime('%H:%M:%S') if v.gps_updated else None,
                'driver': trip.driver_id.name if trip and trip.driver_id else None,
                'trip': trip.name if trip else None,
                'trip_state': trip.state if trip else None,
                'pending_stops': trip.pending_stop_count if trip else 0,
            })

        trip_data = [{
            'id': t.id,
            'name': t.name,
            'state': t.state,
            'driver': t.driver_id.name if t.driver_id else '',
            'vehicle': t.vehicle_id.name if t.vehicle_id else '',
            'plate': t.vehicle_id.plate if t.vehicle_id else '',
            'pending_stops': t.pending_stop_count,
            'stop_count': t.stop_count,
        } for t in active_trips]

        return {'vehicles': vehicle_data, 'trips': trip_data}
