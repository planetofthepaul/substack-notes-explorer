# TakeOnAnything.com — Architecture & Operations Guide

This document explains the full architecture, deployment model, and operational procedures for TakeOnAnything.com.

It is written as a handoff document. Assume:
- The original author is unavailable
- The reader did not design this system
- The reader may not be a professional developer

If this document is followed, the system can be operated and maintained indefinitely.

---

## 1. System overview

TakeOnAnything.com is deliberately split into two completely separate systems:

1. A static frontend website
2. A Python backend API

They do not share code, hosting, or runtime. They communicate only via HTTP requests.

This separation is intentional and should not be collapsed.

---

## 2. Domains and DNS

The domain is split by subdomain:

- takeonanything.com  
  → GitHub Pages (frontend)

- api.takeonanything.com  
  → Hetzner VPS (backend API)

DNS records for these two must remain separate.

Changing one does not affect the other.

---

## 3. Frontend (GitHub Pages)

### 3.1 What the frontend is

The frontend is a static website:
- HTML
- CSS
- JavaScript

There is:
- no server-side logic
- no database
- no secrets

All logic beyond UI lives in the backend API.

---

### 3.2 Where the frontend lives

The frontend is hosted on GitHub Pages.

Relevant paths:
- `/` — main site
- `/notes/index.html` — Notes Exporter UI

GitHub Pages automatically deploys on commit.

---

### 3.3 How the frontend talks to the backend

In `/notes/index.html`, all API calls are routed through a single constant:

```
const API_BASE = 'https://api.takeonanything.com'
```

The frontend makes requests only to:

- POST   /notes/start
- GET    /notes/progress/<job_id>
- GET    /notes/download/<job_id>

No relative paths are used.

If this constant is wrong, the app will fail in Safari.

---

### 3.4 Updating the frontend

To update the frontend:

1. Edit files in the GitHub repository
2. Commit changes
3. Wait for GitHub Pages to redeploy (usually under 1 minute)

No backend restart is required.

---

## 4. Backend (Hetzner VPS)

### 4.1 What the backend is

The backend is a Python API that:
- fetches Substack Notes
- tracks progress in memory
- returns a downloadable text file

It does not render HTML.

---

### 4.2 Server details

- Provider: Hetzner
- OS: Ubuntu 24.04 LTS
- Access: SSH as root

```
ssh root<@SERVER_IP>
```

---

### 4.3 Backend code location

All backend code lives here:

```
/opt/notes-api/
  app.py
  venv/
```

`app.py` is the authoritative backend source.

---

## 5. Runtime stack

Requests flow as follows:

```
Browser
  ↓
nginx
  ↓
Gunicorn
  ↓
Flask (app.py)
```

Components:
- nginx: public-facing web server
- Gunicorn: production Python server
- Flask: application logic
- systemd: process supervisor

---

## 6. systemd service (critical)

The backend runs as a system service:

```
/etc/systemd/system/notes-api.service
```

Service definition:

```
[Unit]
Description=Notes API
After=network.target

[Service]
WorkingDirectory=/opt/notes-api
ExecStart=/opt/notes-api/venv/bin/gunicorn -b 127.0.0.1:8000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

This means:
- the app starts on boot
- the app restarts if it crashes
- closing SSH does not stop it

Useful commands:

```
systemctl status notes-api
systemctl restart notes-api
```

---

## 7. nginx configuration

nginx proxies traffic to the Python app.

Config file:

```
/etc/nginx/sites-available/api.takeonanything.com
```

Enabled via symlink in:

```
/etc/nginx/sites-enabled/
```

If nginx returns **502 Bad Gateway**, the Python app is not running.

Always check:

```
systemctl status notes-api
```

---

## 8. Backend API routes

Health check:

```
GET /
→ notes api running
```

Start export:

```
POST /notes/start
Body: { "subdomain": "example" }
Response: { "job_id": "uuid" }
```

Progress:

```
GET /notes/progress/<job_id>
Response: { count, done, error }
```

Download:

```
GET /notes/download/<job_id>
Returns a text file attachment
```

---

## 9. Job model

Jobs are stored in memory only.

- Restarting the service clears all jobs
- Jobs are expected to be short-lived

This is an intentional design tradeoff.

---

## 10. HTTPS behavior

Frontend HTTPS:
- Provided automatically by GitHub Pages
- Controlled via GitHub Pages settings

Backend HTTPS:
- Must be configured separately via nginx + Let’s Encrypt
- Until configured, browsers (especially Safari) may block HTTPS requests

This is expected during setup.

---

## 11. Common failures

Safari says “Can’t find the server”:
- Cause: HTTPS mismatch or missing certificate
- Fix: wait for TLS or adjust API_BASE

502 Bad Gateway:
- Cause: Python app crashed or dependency missing
- Fix: systemctl status notes-api

Changes not taking effect:
- Backend change → restart service
- Frontend change → wait for GitHub Pages

---

## 12. Updating backend code safely

1. SSH into the server
2. Edit code:

```
nano /opt/notes-api/app.py
```

3. Save
4. Restart:

```
systemctl restart notes-api
```

Never skip the restart.

---

## 13. Design intent

This system is intentionally:
- simple
- cheap to run
- transparent
- easy to debug
- free of vendor lock-in

There is no hidden infrastructure.

If this document is followed, a new maintainer can operate the system safely.
