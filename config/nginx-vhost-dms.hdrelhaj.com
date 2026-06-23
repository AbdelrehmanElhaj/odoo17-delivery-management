# OsmAnd / Traccar Client GPS endpoint
# Flutter app sends to: https://dms.hdrelhaj.com/osmand?id=driver-XXX&lat=...
# Port 5055 is firewalled; this proxies GPS traffic through HTTPS.
location /osmand {
    proxy_pass         http://172.19.0.10:5055/;
    proxy_set_header   Host              $host;
    proxy_set_header   X-Real-IP         $remote_addr;
    proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
}
