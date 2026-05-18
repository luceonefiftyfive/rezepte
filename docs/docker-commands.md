# Docker commands

All Docker-related files for this project are stored in the `docker/` folder.

Use the helper script:

```bash
./docker/rezepte.sh <docker compose command>
```

The stack has two modes:

| Mode | Selection | Files |
|---|---|---|
| Test / development | `REZEPTE_TEST=1` | `docker/.env.test`, `docker/.env.test.secrets`, `docker/docker-compose.test.yml` |
| Production | `REZEPTE_TEST` unset | `docker/.env.prod`, `docker/.env.prod.secrets`, `docker/docker-compose.prod.yml` |

The base Compose file is always:

```text
docker/docker-compose.yml
```

## Initial setup

Create the real environment files from the templates:

```bash
cp docker/.env.test.example docker/.env.test
cp docker/.env.test.secrets.example docker/.env.test.secrets
cp docker/.env.prod.example docker/.env.prod
cp docker/.env.prod.secrets.example docker/.env.prod.secrets
```

Then edit the real files:

```bash
vi docker/.env.test.secrets
vi docker/.env.prod
vi docker/.env.prod.secrets
```

The real `.env*` and `.secrets` files must not be committed.

## Git ignore rules

Add this to the root `.gitignore`:

```gitignore
docker/.env
docker/.env.*
!docker/.env.example
!docker/.env.*.example
docker/certbot/
```

If real S3 keys were already committed, rotate them in the S3 provider console.

## Test system

Start:

```bash
REZEPTE_TEST=1 ./docker/rezepte.sh up -d --build
```

Open:

```text
Frontend:        http://localhost:8080/
Backend health:  http://localhost:8080/api/health
System checks:   http://localhost:8080/api/system/checks
Keycloak:        http://localhost:8080/auth/
MinIO console:   http://localhost:9101/
```

Stop:

```bash
REZEPTE_TEST=1 ./docker/rezepte.sh down
```

Stop and delete test volumes:

```bash
REZEPTE_TEST=1 ./docker/rezepte.sh down -v
```

## Production system

Start:

```bash
./docker/rezepte.sh up -d --build
```

Stop:

```bash
./docker/rezepte.sh down
```

Status:

```bash
sudo ./docker/rezepte.sh ps
```

Logs:

```bash
sudo ./docker/rezepte.sh logs -f nginx
sudo ./docker/rezepte.sh logs -f backend
```

Health:

```bash
curl https://rezepte.unbenet.de/api/health
curl https://rezepte.unbenet.de/api/system/checks
```

## First production certificate setup

The first production certificate setup needs a temporary HTTP-only nginx config.

The final HTTPS config references files that do not exist before certbot has created them:

```text
/etc/letsencrypt/live/rezepte.unbenet.de/fullchain.pem
/etc/letsencrypt/live/rezepte.unbenet.de/privkey.pem
```

First-time flow:

```text
HTTP-only nginx
certbot creates the certificate
switch nginx back to HTTPS config
reload nginx
```

Prerequisites:

```text
rezepte.unbenet.de points to the server IP
Port 80 is reachable from the internet
Port 443 is reachable from the internet
docker/.env.prod contains APP_BASE_URL=https://rezepte.unbenet.de
```

Activate the bootstrap config:

```bash
cp docker/nginx/prod/rezepte.bootstrap.conf docker/nginx/prod/conf.d/rezepte.conf
sudo ./docker/rezepte.sh up -d nginx
```

Check:

```bash
curl http://rezepte.unbenet.de/
```

Expected:

```text
Familienrezepte certificate bootstrap
```

Request the first certificate:

```bash
sudo ./docker/rezepte.sh --profile tools run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email you@example.com \
  --agree-tos \
  --no-eff-email \
  -d rezepte.unbenet.de
```

Check generated files:

```bash
sudo 
```

Switch back to HTTPS:

```bash
cp docker/nginx/prod/rezepte.https.conf docker/nginx/prod/conf.d/rezepte.conf
sudo ./docker/rezepte.sh exec nginx nginx -t
sudo ./docker/rezepte.sh exec nginx nginx -s reload
```

The HTTPS config uses:

```nginx
listen 443 ssl;
http2 on;
```

Do not use:

```nginx
listen 443 ssl http2;
```

## Certificate renewal

Manual check:

```bash
./docker/rezepte.sh --profile tools run --rm certbot renew
./docker/rezepte.sh exec nginx nginx -s reload
```

Dry run:

```bash
./docker/rezepte.sh --profile tools run --rm certbot renew --dry-run
```

Cron example:

```cron
0 3 * * * cd /path/to/familienrezepte && ./docker/rezepte.sh --profile tools run --rm certbot renew --quiet && ./docker/rezepte.sh exec nginx nginx -s reload
```

## Useful checks

Show final Compose config:

```bash
REZEPTE_TEST=1 ./docker/rezepte.sh config
./docker/rezepte.sh config
```

Check nginx config:

```bash
./docker/rezepte.sh exec nginx nginx -t
./docker/rezepte.sh exec nginx nginx -T
```

Check nginx to backend:

```bash
./docker/rezepte.sh exec nginx wget -S -O- http://backend:8000/health
```

Check S3 env vars without printing secrets:

```bash
./docker/rezepte.sh exec backend sh -lc '
for key in S3_ENDPOINT_URL S3_BUCKET S3_ACCESS_KEY S3_SECRET_KEY; do
  if [ -n "${!key:-}" ]; then echo "$key=set"; else echo "$key=missing"; fi
done
'
```

Check MongoDB from the MongoDB container with MongoDB 4.4:

```bash
REZEPTE_TEST=1 ./docker/rezepte.sh exec mongodb sh -lc '
mongo \
  -u "$MONGO_INITDB_ROOT_USERNAME" \
  -p "$MONGO_INITDB_ROOT_PASSWORD" \
  --authenticationDatabase admin \
  --eval "db.adminCommand({ ping: 1 })"
'
```

For MongoDB 5 or newer, use `mongosh` instead of `mongo`.

## Migration from the old layout

From the repository root:

```bash
mkdir -p docker

mv docker-compose.yml docker/docker-compose.yml 2>/dev/null || true
mv docker-compose.test.yml docker/docker-compose.test.yml 2>/dev/null || true
mv docker-compose.prod.yml docker/docker-compose.prod.yml 2>/dev/null || true

mv .env.test docker/.env.test 2>/dev/null || true
mv .env.test.secrets docker/.env.test.secrets 2>/dev/null || true
mv .env.prod docker/.env.prod 2>/dev/null || true
mv .env.prod.secrets docker/.env.prod.secrets 2>/dev/null || true

mv deploy/nginx/certbot docker/certbot 2>/dev/null || true
```

After migration, use:

```bash
./docker/rezepte.sh ...
```

not the old `./scripts/rezepte.sh`.

## Notes

On machines without AVX support, MongoDB 5 or newer may not start.

For the current non-AVX test setup:

```env
MONGODB_IMAGE=mongo:4.4
```

For production on an AVX-capable server:

```env
MONGODB_IMAGE=mongo:7
```
