# Gunicorn Configuration Documentation

## Quick Start

### Development (with auto-reload)
```bash
cd /var/www/PriceSynC/Saas_app
chmod +x run_gunicorn_dev.sh
./run_gunicorn_dev.sh
```

### Production (with systemd)
```bash
# 1. Run setup script (once)
sudo chmod +x setup_gunicorn.sh
sudo ./setup_gunicorn.sh

# 2. Start service
sudo systemctl start gunicorn-saas
sudo systemctl enable gunicorn-saas

# 3. Check status
sudo systemctl status gunicorn-saas
```

## Configuration Files

### `gunicorn_config.py`
- Worker count: CPU * 2 + 1
- Worker class: sync
- Timeout: 30 seconds
- Logs: `/var/log/gunicorn/`

### `start_gunicorn.sh`
- Manual startup script
- Can be used instead of systemd

### `/etc/systemd/system/gunicorn-saas.service`
- Systemd service file
- Auto-restart on failure
- User: www-data
- Working directory: /var/www/PriceSynC/Saas_app

### `/etc/nginx/sites-available/dj.2kvietnam.com`
- Nginx reverse proxy config
- SSL support (requires certificates)
- Static/media file serving
- Security headers

## Deployment Checklist

- [ ] Install Gunicorn: `pip install gunicorn`
- [ ] Create log directories: `mkdir -p /var/log/gunicorn`
- [ ] Set permissions: `chown -R www-data:www-data /var/www/PriceSynC/Saas_app`
- [ ] Test Gunicorn: `./run_gunicorn_dev.sh`
- [ ] Generate SSL cert: `certbot certonly --nginx -d dj.2kvietnam.com`
- [ ] Update Nginx config with SSL paths
- [ ] Enable Nginx site: `ln -sf /etc/nginx/sites-available/dj.2kvietnam.com /etc/nginx/sites-enabled/`
- [ ] Test Nginx: `nginx -t`
- [ ] Restart Nginx: `systemctl restart nginx`
- [ ] Start Gunicorn: `systemctl start gunicorn-saas`
- [ ] Enable auto-start: `systemctl enable gunicorn-saas`
- [ ] Check logs: `tail -f /var/log/gunicorn/error.log`

## Logging

**Access logs:** `/var/log/gunicorn/access.log`
**Error logs:** `/var/log/gunicorn/error.log`

## Monitoring

```bash
# View Gunicorn logs
sudo tail -f /var/log/gunicorn/error.log

# View Nginx logs  
sudo tail -f /var/log/nginx/dj.2kvietnam.com.error.log

# Monitor processes
ps aux | grep gunicorn
systemctl status gunicorn-saas

# Check port 8005
netstat -tlnp | grep 8005
```

## Restart/Reload

```bash
# Soft reload (graceful restart, no downtime)
sudo systemctl reload gunicorn-saas

# Hard restart
sudo systemctl restart gunicorn-saas

# Stop
sudo systemctl stop gunicorn-saas

# Start
sudo systemctl start gunicorn-saas
```

## Troubleshooting

### Port 8005 already in use
```bash
# Kill process using port 8005
fuser -k 8005/tcp
```

### Permission denied errors
```bash
# Fix permissions
sudo chown -R www-data:www-data /var/www/PriceSynC/Saas_app
sudo chown -R www-data:www-data /var/log/gunicorn
```

### Gunicorn not starting
```bash
# Check systemd logs
sudo journalctl -u gunicorn-saas -n 50

# Check error log
sudo cat /var/log/gunicorn/error.log
```

### Nginx returning 502 Bad Gateway
1. Check if Gunicorn is running: `systemctl status gunicorn-saas`
2. Check if port 8005 is listening: `netstat -tlnp | grep 8005`
3. Check Nginx error log: `sudo tail -f /var/log/nginx/dj.2kvietnam.com.error.log`

## Performance Tuning

### Increase workers (for high traffic)
Edit `/etc/systemd/system/gunicorn-saas.service`:
```
ExecStart=... --workers 8 ...
```

### Increase timeouts
Edit `gunicorn_config.py`:
```python
timeout = 60  # Increase from 30
```

### Enable keepalive
Already enabled with `keepalive = 2` in config

## Security

- [ ] Enable HTTPS/SSL
- [ ] Set strong SECRET_KEY in Django
- [ ] Update ALLOWED_HOSTS in settings.py
- [ ] Set DEBUG=False in production
- [ ] Configure firewall to allow only 80, 443, 22
- [ ] Disable admin hash in production settings

## Environment Variables

Set in `/etc/systemd/system/gunicorn-saas.service`:
```
Environment="DJANGO_SETTINGS_MODULE=config.settings"
Environment="PYTHONUNBUFFERED=1"
```

## Additional Resources

- Gunicorn docs: https://docs.gunicorn.org/
- Nginx docs: https://nginx.org/en/docs/
- Django deployment: https://docs.djangoproject.com/en/4.2/howto/deployment/
