# Deployment Notes

## Dedicated Egress IP Addresses

The following dedicated egress IP addresses have been enabled for this application on DigitalOcean:

- `139.59.183.23`
- `134.209.18.213`

These IPs are used for all outbound traffic from the server. If this application connects to external services that use IP-based firewalls or allow-lists, you should add these IP addresses to those services' configurations.

For example, the application makes calls to Google AI services from the backend (`server.js`). If your Google Cloud project has firewall rules, you may need to add these IPs to allow connections from your application.

**Note:** These IPs are for *outbound* traffic from the server. They are not used for incoming traffic from users' browsers. The information you found about `apphosting.yaml` is for Google Cloud App Hosting and does not apply to your DigitalOcean application.
