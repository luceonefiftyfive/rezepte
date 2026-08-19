# Production Certificate Renewal Guide

This project uses Certbot to request and renew the TLS certificate for the production domain. The certificate files are mounted into the Nginx container and reloaded after renewal.

## Prerequisites

- The production domain points to the correct server IP.
- Ports 80 and 443 are reachable from the internet.
- Docker Compose is installed and available on the server.
- You are running the commands from the project root.

## Regular Renewal

Run the following commands to renew the certificate:

```bash
cd /path/to/project
sudo ./docker/rezepte.sh --profile tools run --rm certbot renew
sudo ./docker/rezepte.sh exec nginx nginx -s reload
```

A dry run is also useful before renewing:

```bash
sudo ./docker/rezepte.sh --profile tools run --rm certbot renew --dry-run
```

## If the Certificate Has Already Expired

If the certificate has expired, Certbot may not be able to validate the domain unless Nginx temporarily serves the ACME challenge over HTTP.

Switch Nginx to the bootstrap configuration:

```bash
cd /path/to/project
cp docker/nginx/prod/rezepte.bootstrap.conf docker/nginx/prod/conf.d/rezepte.conf
sudo ./docker/rezepte.sh up -d nginx
```

Then request a new certificate:

```bash
sudo ./docker/rezepte.sh --profile tools run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email your-email@example.com \
  --agree-tos \
  --no-eff-email \
  -d your-domain.example
```

After the certificate is issued, switch Nginx back to the HTTPS configuration:

```bash
cp docker/nginx/prod/rezepte.https.conf docker/nginx/prod/conf.d/rezepte.conf
sudo ./docker/rezepte.sh exec nginx nginx -t
sudo ./docker/rezepte.sh exec nginx nginx -s reload
```

## Automatic Renewal

To renew automatically, add a cron job like the following:

```cron
0 3 * * * cd /path/to/project && ./docker/rezepte.sh --profile tools run --rm certbot renew --quiet && ./docker/rezepte.sh exec nginx nginx -s reload
```

This runs renewal daily at 03:00 and reloads Nginx after a successful renewal.

## Verification

After renewal or reissue, verify that HTTPS is functioning correctly:

```bash
sudo ./docker/rezepte.sh exec nginx nginx -t
sudo ./docker/rezepte.sh exec nginx nginx -s reload
curl -I https://your-domain.example
```

If the request returns a valid HTTPS response, the certificate is working correctly.

## Notes

- Certbot stores the certificate in the Letsencrypt directory mounted by Docker.
- The ACME challenge must be reachable on port 80 for validation to succeed.
- If SSL errors continue after renewal, check the Nginx configuration and confirm certificate paths are correct.
