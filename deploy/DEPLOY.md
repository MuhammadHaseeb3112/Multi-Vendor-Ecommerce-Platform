# Deploying MarketHub (public demo)

For a Linux server with Docker that already runs a Caddy reverse proxy on
ports 80/443 and a shared Docker network called `edge`. MarketHub publishes no
ports of its own; Caddy reaches it as `markethub-web:8000`.

Needs about 0.5 GB RAM and 1.5 GB disk. Works on x86-64 and ARM64.

## 1. Domain

Point a (sub)domain at the server, e.g. a DuckDNS name such as
`mh-markethub.duckdns.org`.

## 2. Get the code and configure

```bash
git clone https://github.com/MuhammadHaseeb3112/Multi-Vendor-Ecommerce-Platform.git markethub
cd markethub
cp deploy/env.prod.example deploy/.env.prod
nano deploy/.env.prod        # SECRET_KEY, POSTGRES_PASSWORD, your domain
```

## 3. Start

```bash
df -h /                       # check there is at least 5 GB free first
docker network create edge 2>/dev/null || true
docker compose -p markethub -f deploy/compose.prod.yml --env-file deploy/.env.prod up -d --build
docker compose -p markethub -f deploy/compose.prod.yml --env-file deploy/.env.prod ps
```

On first start the container runs migrations and, because `DEMO_MODE=True`,
loads the demo data set (demo logins, 5 stores, 26 products, 30 orders).

## 4. Add the site to Caddy

In the Caddyfile of the stack that owns ports 80/443:

```
markethub.example.com {
	encode zstd gzip
	header {
		Strict-Transport-Security "max-age=31536000"
		-Server
	}
	reverse_proxy markethub-web:8000
}
```

Reload that Caddy. It gets the HTTPS certificate by itself.

## 5. Nightly reset (keeps the demo clean)

```bash
crontab -e
# 03:30 every night
30 3 * * * cd ~/markethub && docker compose -p markethub -f deploy/compose.prod.yml --env-file deploy/.env.prod exec -T markethub-web python manage.py seed_demo --reset >> ~/markethub-reset.log 2>&1
```

## Updating

```bash
cd ~/markethub && git pull
docker compose -p markethub -f deploy/compose.prod.yml --env-file deploy/.env.prod up -d --build
```

## What demo mode does

- The login page offers one-click roles. "Customer" creates a private visitor
  account (with sample orders) so each visitor shops in their own space.
- The shared Vendor and Admin logins are read-only: every page opens, nothing
  submitted is saved, so all visitors see the same clean data.
- Reviews, product questions, sign-ups, password and profile changes are off.
- No email is sent.
- Django's built-in `/admin/` is switched off; the app's own admin panel stays.
