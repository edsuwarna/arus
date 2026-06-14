# Deployment Guide

Guide for deploying Arus in production environments.

---

## Prerequisites

- **Linux server** (Ubuntu 22.04+ or Debian 12+ recommended)
- **Docker** 24+ & **Docker Compose** v2+
- **Minimum**: 2 CPU cores, 4GB RAM, 20GB disk
- **Recommended**: 4 CPU cores, 8GB RAM, 50GB SSD
- **Domain name** (optional, for HTTPS setup)
- **Reverse proxy** (nginx, Caddy, or Cloudflare Tunnel)

---

## Production Deployment

### 1. Server Preparation

```bash
# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
```

### 2. Deploy with Docker Compose

```bash
# Create project directory
mkdir -p /opt/arus && cd /opt/arus

# Download docker-compose.yml
curl -O https://<your-site>/docker-compose.yml

cp .env.example .env
```

### 3. Set Secure Secrets

Edit `.env` with **strong, unique values**:

```bash
# Generate a secure JWT secret
openssl rand -hex 32
# Output: <jwt-secret>

# Generate a secure encryption key
openssl rand -hex 32
# Output: <encryption-key>

# Edit .env with these values
ARUS_JWT_SECRET=<jwt-secret>
ARUS_ENCRYPTION_KEY=<encryption-key>

# Set a strong database password
ARUS_DB_PASSWORD=<strong-db-password>
```

### 4. Configure Reverse Proxy (HTTPS)

#### Option A: nginx with Let's Encrypt

Create `/etc/nginx/sites-available/arus`:

```nginx
server {
    listen 80;
    server_name arus.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name arus.example.com;

    ssl_certificate /etc/letsencrypt/live/arus.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/arus.example.com/privkey.pem;

    # Arus Console (SPA)
    location / {
        proxy_pass http://127.0.0.1:8082;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Arus API
    location /api/ {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Option B: Cloudflare Tunnel

```bash
# Install cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared

# Authenticate and create tunnel
cloudflared tunnel login
cloudflared tunnel create arus

# Configure tunnel
cloudflared tunnel route dns arus arus.example.com
```

Create `~/.cloudflared/config.yml`:
```yaml
tunnel: <tunnel-id>
credentials-file: /root/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: arus.example.com
    service: http://localhost:8082
  - service: http_status:404
```

### 5. Start Services

```bash
docker compose up -d
```

Verify all containers are healthy:
```bash
docker compose ps
docker compose logs arus-api | tail -5
```

### 6. Configure Firewall

```bash
# Docker exposes ports 8081 and 8082 - bind only to localhost
# Edit docker-compose.yml:
ports:
  - "127.0.0.1:8081:8081"
  - "127.0.0.1:8082:80"

# Then restart
docker compose up -d

# Configure firewall
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

---

## Security Checklist

- [ ] **Change default credentials**: Log in as `admin@arus.io` and change the password immediately, or delete the default admin and create your own
- [ ] **Set strong `ARUS_JWT_SECRET`**: At least 32 bytes of random hex
- [ ] **Set strong `ARUS_ENCRYPTION_KEY`**: At least 32 bytes of random hex
- [ ] **Set strong database password**
- [ ] **Use HTTPS**: Never expose Arus over plain HTTP in production
- [ ] **Bind to localhost**: Don't expose Docker ports publicly; use a reverse proxy
- [ ] **Restrict API access**: Use firewall rules to limit access to the API port
- [ ] **Database backups**: Configure automated PostgreSQL backups
- [ ] **Source DB permissions**: Use read-only (SELECT-only) accounts for source connectors
- [ ] **Audit user accounts**: Regularly review active users and their roles
- [ ] **Rate limiting**: Login endpoint is rate-limited by default (10 attempts/60s per IP)

---

## Scaling

### Vertical Scaling

Arus is designed for single-host deployment. To scale vertically:

- **Increase RAM**: More memory allows larger batch sizes and more concurrent pipelines
- **Faster CPU**: Reduces extraction/transformation time
- **SSD storage**: Faster database I/O for watermarks and run logs

### Concurrent Pipelines

The default configuration supports 5 concurrent pipelines on 2-core / 4GB RAM. Adjust APScheduler settings in code if needed.

### Batch Size Optimization

- Default: 10,000 rows per batch
- Increase for large tables with wide rows (reduces round trips)
- Decrease for tables with frequent small updates (reduces latency)

### Connection Pooling

The API uses SQLAlchemy connection pooling (pool_size=10, max_overflow=5). Adjust in `arus/shared/db/session.py` if needed.

---

## Monitoring

### Health Check

```bash
curl http://localhost:8081/api/health
# {"status":"ok","data":{"version":"0.1.0","database":"connected","scheduler":"running"}}
```

### Container Monitoring

```bash
# Check container health
docker compose ps

# View logs
docker compose logs -f arus-api
docker compose logs -f arus-console

# Resource usage
docker stats
```

### Prometheus / Grafana (Optional)

Add metrics endpoint to the API if monitoring is needed. The current version has no built-in metrics export.

### Log Aggregation (Optional)

Configure Docker log driver to ship logs to your logging platform:

```yaml
# docker-compose.yml
x-logging: &default-logging
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"

services:
  arus-api:
    logging: *default-logging
```

---

## Backup & Recovery

### Database Backup

```bash
# Manual backup
docker exec arus-db pg_dump -U arus arus_warehouse > arus_backup_$(date +%Y%m%d).sql

# Automated daily backup (add to crontab)
0 2 * * * docker exec arus-db pg_dump -U arus arus_warehouse > /backups/arus_$(date +\%Y\%m\%d).sql && gzip /backups/arus_$(date +\%Y\%m\%d).sql
```

### Database Restore

```bash
# Stop API (to prevent writes)
docker compose stop arus-api

# Restore from backup
cat arus_backup.sql | docker exec -i arus-db psql -U arus arus_warehouse

# Restart API
docker compose start arus-api
```

### Full System Recovery

1. Restore database from backup
2. Restore `.env` configuration
3. Run `docker compose up -d`
4. Verify health: `curl http://localhost:8081/api/health`

---

## Upgrading

### Standard Upgrade

```bash
cd /opt/arus

# Pull latest code
git pull

# Rebuild and restart
docker compose build --no-cache
docker compose up -d

# Run any pending migrations (handled automatically on startup)
```

### Rollback

```bash
# Revert code
git checkout <previous-tag>

# Rebuild and restart
docker compose build --no-cache
docker compose up -d
```

---

## Troubleshooting Production Issues

| Issue | Check | Solution |
|---|---|---|
| API won't start | `docker compose logs arus-api` | Check DB connection, env vars, port conflicts |
| Database connection refused | `docker compose logs arus-db` | Verify DB host/port in `.env`, check if DB container is running |
| Pipelines stuck "running" | Check Run Logs in Console | The run may have timed out without cleanup. Check executor logs. |
| Console shows 502 errors | Check nginx and API connectivity | Ensure `arus-api` is healthy and reachable from `arus-console` |
| Out of memory | `docker stats` | Reduce batch size, concurrent pipelines, or add more RAM |
| Disk full | `df -h` | Clean old Docker images, prune logs, reduce run log retention |
| Slow pipeline performance | Check source DB load, network latency | Optimize queries, reduce batch size, check index usage |
| SSL certificate expired | Certbot or Cloudflare status | Renew Let's Encrypt cert or check Cloudflare tunnel status |
