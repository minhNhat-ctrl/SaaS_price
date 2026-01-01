"""
Gunicorn Configuration for PriceSynC SaaS App
"""
import multiprocessing
import os

# Server socket - ONLY localhost, không public ra internet
bind = '127.0.0.1:8005'
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 30
keepalive = 2

# Process naming
proc_name = 'gunicorn-saas-app'

# Environment variables
raw_env = [
    'PYTHONPATH=/var/www/PriceSynC',
    'DJANGO_SETTINGS_MODULE=config.settings',
]

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Logging
accesslog = '/var/log/gunicorn/access.log'
errorlog = '/var/log/gunicorn/error.log'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process hooks
def on_starting(server):
    print("[GUNICORN] Gunicorn server starting")

def on_exit(server):
    print("[GUNICORN] Gunicorn server stopped")

def when_ready(server):
    print("[GUNICORN] Gunicorn server ready. Listening on {}".format(bind))

def worker_int(worker):
    print("[GUNICORN] Worker {} received INT or QUIT signal".format(worker.pid))

def pre_fork(server, worker):
    pass

def post_fork(server, worker):
    print("[GUNICORN] Worker {} spawned".format(worker.pid))

def pre_exec(server):
    print("[GUNICORN] Forked child, re-executing.")

def worker_abort(worker):
    print("[GUNICORN] Worker {} aborted".format(worker.pid))
