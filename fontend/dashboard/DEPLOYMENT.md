# 🚀 Deployment Guide - app.2kvietnam.com

## Prerequisites ✅

- [x] Node.js 20.x installed
- [x] npm installed
- [x] Nginx installed
- [x] Certbot installed
- [x] Dependencies installed

## Quick Deploy

```bash
cd /var/www/PriceSynC/Saas_app/fontend/dashboard
./deploy.sh
```

## Manual Steps

### 1. Build Production

```bash
cd /var/www/PriceSynC/Saas_app/fontend/dashboard
npm run build
```

### 2. Configure Nginx

```bash
# Copy nginx config
sudo cp nginx.conf /etc/nginx/sites-available/app.2kvietnam.com

# Enable site
sudo mkdir -p /etc/nginx/sites-enabled
sudo ln -sf /etc/nginx/sites-available/app.2kvietnam.com /etc/nginx/sites-enabled/

# Test config
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### 3. Setup SSL

```bash
# Get SSL certificate
sudo certbot --nginx -d app.2kvietnam.com --non-interactive --agree-tos --email admin@2kvietnam.com

# Auto-renewal (already configured)
sudo certbot renew --dry-run
```

### 4. Verify

```bash
# Check nginx status
sudo systemctl status nginx

# Test site
curl -I https://app.2kvietnam.com

# View logs
sudo tail -f /var/log/nginx/app.2kvietnam.com.access.log
```

## Post-Deployment

### Update Frontend

```bash
cd /var/www/PriceSynC/Saas_app/fontend/dashboard
git pull  # if using git
npm run build
sudo systemctl reload nginx
```

### Rollback

```bash
# Keep old builds
cp -r build build.backup.$(date +%Y%m%d)

# Restore if needed
rm -rf build
mv build.backup.YYYYMMDD build
```

## Troubleshooting

### Build Failed

```bash
# Clear cache
rm -rf node_modules package-lock.json
npm install --legacy-peer-deps
npm run build
```

### Nginx 502 Error

```bash
# Check nginx logs
sudo tail -50 /var/log/nginx/error.log

# Check if backend is running
curl http://localhost:8000/api/health
```

### SSL Issues

```bash
# Renew certificate
sudo certbot renew --force-renewal

# Check certificate
sudo certbot certificates
```

## Monitoring

```bash
# Real-time logs
sudo tail -f /var/log/nginx/app.2kvietnam.com.access.log

# Error logs
sudo tail -f /var/log/nginx/app.2kvietnam.com.error.log

# Nginx reload
sudo nginx -s reload
```

## URLs

- **Production**: https://app.2kvietnam.com
- **API Backend**: http://localhost:8000 (proxied through nginx)

---

**Last updated**: 31 Dec 2025
