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

## 6. Database backups

`deploy/backup.sh` dumps the database to `~/backups/markethub/` (gzip, owner-only
permissions) and keeps the last 14 days. Run it from cron a few minutes before
the nightly reset:

```bash
crontab -e
# 22:15 UTC (03:15 in Pakistan), before the demo reset
15 22 * * * bash ~/markethub/deploy/backup.sh >> ~/markethub-backup.log 2>&1
```

Restore a backup:

```bash
gunzip -c ~/backups/markethub/markethub-YYYYmmdd-HHMM.sql.gz | \
  docker compose -p markethub -f deploy/compose.prod.yml --env-file deploy/.env.prod \
    exec -T db psql -U markethub -d markethub
```

## Updating

By hand, with a health check and automatic rollback:

```bash
cd ~/markethub && bash deploy/deploy.sh
```

## Automatic deploys (GitHub Actions)

Every push runs the tests on PostgreSQL (`.github/workflows/ci.yml`). When
they pass on `main`, `.github/workflows/deploy.yml` connects to the server over
SSH and runs `deploy/deploy.sh`: it pulls the new code, rebuilds, waits for the
container health check and for the site through Caddy, and goes back to the
previous version if either fails.

Turn it on once, in the GitHub repository under
**Settings → Secrets and variables → Actions**:

| Kind | Name | Value |
|---|---|---|
| Secret | `DEPLOY_HOST` | the server's public IP |
| Secret | `DEPLOY_USER` | `ubuntu` |
| Secret | `DEPLOY_SSH_KEY` | a private key whose public key is in the server's `~/.ssh/authorized_keys` |
| Variable | `DEPLOY_ENABLED` | `true` |
| Variable | `DEPLOY_URL` | `https://mh-markethub.duckdns.org` |

A deploy can also be started by hand from the **Actions** tab (Deploy → Run workflow).

## What demo mode does

- The login page offers one-click roles. "Customer" and "Vendor" create a
  private visitor account; a vendor gets their own copy of a store to manage.
  Visitors never see each other's data.
- The shared Admin login is read-only: every page opens, nothing submitted is
  saved, so all visitors see the same clean marketplace.
- Reviews, product questions, sign-ups, password and profile changes are off.
- No email is sent.
- Django's built-in `/admin/` is switched off; the app's own admin panel stays.
