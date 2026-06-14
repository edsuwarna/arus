# Security Guide

Best practices for securing Arus in production environments.

---

## Quick Checklist

- [ ] **Change default admin password** immediately after first login
- [ ] **Set strong `ARUS_JWT_SECRET`** (at least 32 random hex bytes)
- [ ] **Set strong `ARUS_ENCRYPTION_KEY`** (at least 32 random hex bytes)
- [ ] **Use HTTPS** — never expose Arus over plain HTTP
- [ ] **Bind Docker ports to localhost** — don't expose API/Console ports directly
- [ ] **Use a reverse proxy** (nginx, Caddy, Cloudflare Tunnel)
- [ ] **Restrict API access** via firewall rules
- [ ] **Use read-only source DB accounts**
- [ ] **Configure automated database backups**
- [ ] **Audit user accounts** regularly
- [ ] **Keep Docker and system updated**

---

## Authentication

### JWT Token Management

Arus uses JWT-based authentication with access and refresh tokens:

| Token | Lifetime | Purpose |
|-------|----------|---------|
| Access token | 15 minutes | API authorization (short-lived) |
| Refresh token | 7 days | Obtain new access tokens |

**Best practices:**
- Tokens are stored in `localStorage` by the Console SPA
- Log out when not using the Console (clears tokens)
- The refresh endpoint accepts `X-Refresh-Token` header (auto-renewed by the Console on page load)
- Tokens cannot be revoked server-side — rotate the `ARUS_JWT_SECRET` if compromised

### Admin Account

The default installation creates an admin account:

- **Email:** `admin@arus.io`
- **Password:** `admin123`

**Immediately after first login:**
1. Go to **Settings** → **Users**
2. Create a new admin account with your email
3. Delete the default `admin@arus.io` account
4. Alternatively, change the password via user edit

### Password Policy

- Passwords are hashed with **bcrypt** via `passlib`
- No built-in complexity requirements — enforce at the organization level
- Consider rotating passwords periodically

---

## Role-Based Access Control

Arus has three built-in roles:

| Role | Permissions |
|------|-------------|
| **Admin** | Full access — user management, settings, all CRUD operations |
| **Editor** | Create/edit sources, pipelines, destinations; trigger runs |
| **Viewer** | Read-only — view dashboards, pipeline details, run history |

**Principle of least privilege:** Assign users the minimum role they need.

---

## Network Security

### Docker Port Binding

**Never bind Arus ports to `0.0.0.0` (all interfaces).** Instead, bind to localhost:

```yaml
# docker-compose.yml
services:
  arus-api:
    ports:
      - "127.0.0.1:8081:8081"   # Only accessible from the host

  arus-console:
    ports:
      - "127.0.0.1:8082:80"     # Only accessible from the host
```

### Reverse Proxy (HTTPS)

Always terminate TLS at the reverse proxy:

#### Option A: nginx with Let's Encrypt

```nginx
server {
    listen 443 ssl http2;
    server_name arus.example.com;

    ssl_certificate /etc/letsencrypt/live/arus.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/arus.example.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Arus Console
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

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name arus.example.com;
    return 301 https://$server_name$request_uri;
}
```

#### Option B: Cloudflare Tunnel (No open ports)

```bash
cloudflared tunnel create arus
cloudflared tunnel route dns arus arus.example.com
```

```yaml
# ~/.cloudflared/config.yml
tunnel: <tunnel-id>
credentials-file: /root/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: arus.example.com
    service: http://localhost:8082
  - service: http_status:404
```

Advantage: **zero open ports** on your server — everything tunnels through Cloudflare.

### Firewall Rules

```bash
# Allow only SSH, HTTP, and HTTPS
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp          # SSH
ufw allow 80/tcp          # HTTP (for Let's Encrypt)
ufw allow 443/tcp         # HTTPS
ufw enable
```

If using Cloudflare Tunnel, only port 22 (SSH) needs to be open — the tunnel handles the rest.

---

## Secrets Management

### Required Secrets

Generate these during production setup:

```bash
# Generate JWT secret (32 random hex bytes)
openssl rand -hex 32

# Generate encryption key (32 random hex bytes)
openssl rand -hex 32
```

Set them in `.env`:

```bash
ARUS_JWT_SECRET=<jwt-secret>
ARUS_ENCRYPTION_KEY=<encryption-key>
ARUS_DB_PASSWORD=<strong-db-password>
```

### Important Notes

- `ARUS_JWT_SECRET` is used for signing JWT tokens — changing it invalidates all existing sessions
- `ARUS_ENCRYPTION_KEY` is used for Fernet encryption of stored source/destination passwords — changing it makes existing encrypted credentials unreadable (you'll need to re-enter passwords for all sources/destinations)
- If `ARUS_ENCRYPTION_KEY` is not set, it's automatically derived from `ARUS_JWT_SECRET`

### .env File Protection

```bash
# Restrict permissions
chmod 600 .env

# Do not commit .env to version control (already in .gitignore)
```

---

## Database Security

### Source Database

- **Create a dedicated read-only user** for each source connector
- Grant only `SELECT` privileges on the databases/tables being synced
- Restrict source access to the Arus server's IP

```sql
-- Example for MySQL source
CREATE USER 'arus_reader'@'192.168.1.%' IDENTIFIED BY 'strong_password';
GRANT SELECT ON ecommerce.* TO 'arus_reader'@'192.168.1.%';
```

### Warehouse Database

- The Arus database (`arus_warehouse`) contains config, state, and data
- Access it only from the Arus API container (not exposed externally)
- Configure regular automated backups
- Use schema-level separation (`arus_config`, `arus_state`, `arus_run_logs`, `staging`, `analytics`)

### Credential Storage

- Source/destination passwords are encrypted at rest using **Fernet (AES-128-CBC)**
- The encryption key is derived from `ARUS_ENCRYPTION_KEY` or `ARUS_JWT_SECRET`
- Passwords are never returned in API responses (masked as `****`)

---

## Rate Limiting

The login endpoint is protected against brute-force attacks:

- **10 attempts per 60 seconds per IP address**
- In-memory tracking (resets on API restart)
- After exceeding the limit, the API returns `429 Too Many Requests`

This only covers the login endpoint. For comprehensive rate limiting, add at the reverse proxy level:

```nginx
# nginx rate limiting
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/s;

server {
    location /api/ {
        limit_req zone=api_limit burst=50 nodelay;
        proxy_pass http://127.0.0.1:8081;
    }
}
```

---

## Backup & Recovery

### Database Backup

```bash
# Manual backup
docker exec arus-db pg_dump -U arus arus_warehouse > arus_backup.sql

# Automated daily backup (via crontab)
0 2 * * * docker exec arus-db pg_dump -U arus arus_warehouse > /backups/arus_$(date +\%Y\%m\%d).sql && gzip /backups/arus_$(date +\%Y\%m\%d).sql && find /backups -name "*.sql.gz" -mtime +30 -delete
```

### Database Restore

```bash
# Stop API (prevents writes during restore)
docker compose stop arus-api

# Restore from backup
cat arus_backup.sql | docker exec -i arus-db psql -U arus arus_warehouse

# Restart API
docker compose start arus-api
```

### Configuration Backup

Back up your `.env` file separately — it contains secrets needed for recovery.

---

## Security Considerations by Component

### arus-api

| Concern | Mitigation |
|---------|------------|
| JWT secret leakage | Rotate immediately — all tokens become invalid |
| Dependency CVEs | Keep Python dependencies updated (`pip install -r requirements.txt --upgrade`) |
| SQL injection | All queries use parameterized SQLAlchemy — not vulnerable |
| XSS | Console is a single-page app fetching data via JSON API — no server-side rendering |

### arus-console

| Concern | Mitigation |
|---------|------------|
| XSS | Console renders data from API using `textContent`, not `innerHTML` |
| CSRF | JWT tokens are required for all mutations; tokens not accessible cross-origin |
| Token theft | Access tokens expire in 15 minutes; refresh tokens in 7 days |

### arus-db

| Concern | Mitigation |
|---------|------------|
| Exposed port | PostgreSQL port is internal to Docker network only |
| Unencrypted connections | Database is internal to Docker network — encryption adds overhead with minimal benefit |
| Data at rest | Database files are on Docker volume — encrypt the underlying disk for FDE |

---

## Incident Response

### If you suspect a compromise:

1. **Stop the API**: `docker compose stop arus-api`
2. **Rotate secrets**: Change `ARUS_JWT_SECRET` and `ARUS_ENCRYPTION_KEY`
3. **Audit users**: Delete any unknown user accounts via database
4. **Check run logs**: Look for suspicious pipeline activity
5. **Restore from backup** if data integrity is in question
6. **Review system logs**: `journalctl -u docker` or `/var/log/syslog`
7. **Rotate source database passwords** that were configured in Arus
8. **Restart**: `docker compose up -d`

### Reporting Vulnerabilities

If you discover a security vulnerability in Arus, please contact the maintainer directly. Do not open public issues for security vulnerabilities.
