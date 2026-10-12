# 🚀 Server Deployment & Setup Guide

Complete guide for deploying **GENAI Studio** on an **Oracle Cloud Infrastructure (OCI) VM** using **systemd**, **Nginx reverse proxy**, and **Certbot (SSL/HTTPS)**.

---

## 📌 Architecture & Server Details

* **VM Public IP:** `129.225.111.80`
* **Domain Name:** `genaisample.duckdns.org`
* **Default OS User:** `opc` (Oracle Linux / RHEL)
* **Application Path:** `/home/opc/GENAI`
* **Virtualenv Path:** `/home/opc/GENAI/venv`
* **Internal App Port:** `127.0.0.1:8080` (Django runserver / gunicorn)
* **Public Ports:** `80` (HTTP) & `443` (HTTPS)

---

## 📋 Step 1: VM Prerequisites & Initial Setup

SSH into your Oracle Cloud VM:
```bash
ssh -i /path/to/your/private_key opc@129.225.111.80
```

### 1. Update Packages & Install Dependencies
On Oracle Linux / RHEL / CentOS:
```bash
sudo dnf update -y
sudo dnf install python3-pip -y
sudo pip3 install certbot certbot-nginx
certbot --version
```
*(On Ubuntu/Debian, use `sudo apt update && sudo apt install -y git python3 python3-venv python3-pip nginx certbot python3-certbot-nginx`)*

### 2. Clone the Repository
```bash
cd /home/opc
git clone https://github.com/<your-username>/GENAI.git
cd /home/opc/GENAI
```

### 3. Create Virtual Environment & Install Requirements
```bash
python3 -m venv /home/opc/GENAI/venv
/home/opc/GENAI/venv/bin/pip install --upgrade pip
/home/opc/GENAI/venv/bin/pip install -r /home/opc/GENAI/requirements.txt
```

### 4. Create the Production `.env` File
Create `/home/opc/GENAI/.env`:
```bash
nano /home/opc/GENAI/.env
```
Add your production secrets:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
UNIVERSAL_AGENT_PASSWORD=your_secure_password_here
OLLAMA_BASE_URL=http://localhost:11434
DEBUG=True
ALLOWED_HOSTS=genaisample.duckdns.org,129.225.111.80,localhost,127.0.0.1
```
*(Save with `Ctrl+O`, then exit with `Ctrl+X`)*

---

## ⚙️ Step 2: Systemd Service Setup (`genai.service`)

The systemd service keeps your Django application running 24/7 in the background and restarts it automatically on system reboots or crashes.

### 1. Copy the Service File
Copy `scripts/genai.service` to the system systemd directory:
```bash
sudo cp /home/opc/GENAI/scripts/genai.service /etc/systemd/system/genai.service
```

### 2. Verify Service File Contents
Verify `/etc/systemd/system/genai.service`:
```ini
[Unit]
Description=GENAI API Service
After=network.target

[Service]
User=opc
WorkingDirectory=/home/opc/GENAI
ExecStart=/home/opc/GENAI/venv/bin/python3 /home/opc/GENAI/manage.py runserver 0.0.0.0:8080
Restart=always
Environment="PATH=/home/opc/GENAI/venv/bin"

[Install]
WantedBy=multi-user.target
```

### 3. Reload, Enable & Start the Service
```bash
# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable service to start automatically on system boot
sudo systemctl enable genai.service

# Start the service
sudo systemctl start genai.service

# Check service status
sudo systemctl status genai.service
```

### 🛠️ Useful Systemd Commands
```bash
# View live logs
sudo journalctl -u genai.service -f

# Restart service after code changes
sudo systemctl restart genai.service

# Stop service
sudo systemctl stop genai.service
```

---

## 🌐 Step 3: Nginx Reverse Proxy Setup (`nginx.conf`)

Nginx routes public requests from `genaisample.duckdns.org` on ports 80/443 to the internal Django service running on `127.0.0.1:8080`.

### 1. Place the Nginx Configuration
On Oracle Linux / RHEL:
```bash
sudo cp /home/opc/GENAI/scripts/genai.conf /etc/nginx/conf.d/genai.conf
```
*(On Ubuntu/Debian: `sudo cp /home/opc/GENAI/scripts/nginx.conf /etc/nginx/sites-available/genai` followed by `sudo ln -s /etc/nginx/sites-available/genai /etc/nginx/sites-enabled/`)*

### 2. Initial Configuration for First-Time Setup
If you haven't generated SSL certificates yet, Nginx will fail if port `443 ssl` is configured without certs. 

For the first-time setup before Certbot runs, configure port 80 to proxy directly:
```nginx
server {
    listen 80;
    server_name genaisample.duckdns.org;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Test & Start Nginx
```bash
# Test configuration syntax
sudo nginx -t

# Enable and start Nginx
sudo systemctl enable nginx
sudo systemctl restart nginx
```

---

## 🔒 Step 4: Free SSL / HTTPS Setup with Certbot

Once your domain `genaisample.duckdns.org` is pointing to `129.225.111.80` and Nginx is running, obtain free Let's Encrypt certificates:

```bash
sudo /usr/local/bin/certbot --nginx -d genaisample.duckdns.org
```

Certbot will:
1. Verify domain ownership via HTTP.
2. Generate SSL certificates under `/etc/letsencrypt/live/genaisample.duckdns.org/`.
3. Automatically update your `/etc/nginx/conf.d/genai.conf` to redirect HTTP (port 80) to HTTPS (port 443) and bind the certificates.
4. Reload Nginx.

### Verify Certificate Auto-Renewal
```bash
sudo certbot renew --dry-run
```

---

## 🛡️ Step 5: Oracle Cloud Firewall & Security Rules (Important!)

Oracle Cloud VMs block incoming ports 80 and 443 by default. You must open them in **both** the OCI Console and the OS firewall:

### 1. OCI Cloud Console Security List (Ingress Rules)
1. Go to **Oracle Cloud Console** -> **Networking** -> **Virtual Cloud Networks (VCN)**.
2. Select your VCN -> Click **Security Lists** -> Click **Default Security List**.
3. Under **Ingress Rules**, click **Add Ingress Rules**:
   * **Rule 1 (HTTP):**
     * Source CIDR: `0.0.0.0/0`
     * IP Protocol: `TCP`
     * Destination Port Range: `80`
   * **Rule 2 (HTTPS):**
     * Source CIDR: `0.0.0.0/0`
     * IP Protocol: `TCP`
     * Destination Port Range: `443`

### 2. OS Firewall (`firewalld` on Oracle Linux)
Run inside the VM terminal:
```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --reload
```
*(If the OS uses `iptables` directly:)*
```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save  # or sudo service iptables save
```

---

## 🔄 Step 6: Automated CI/CD Deployments (GitHub Actions)

Your repository includes `.github/workflows/deploy.yml`. Whenever you push changes to `main`:

```yaml
- name: Deploy to Oracle VM via SSH
  uses: appleboy/ssh-action@9b978f09f2587beff9c80449f57cb0f0612d3039
  with:
    host: 129.225.111.80
    username: opc
    key: ${{ secrets.ORACLE_VM_SSH_KEY }}
    script: |
      cd /home/opc/GENAI
      git pull origin main
      ./venv/bin/pip install -r requirements.txt
      sudo systemctl restart genai.service
```

### Setup GitHub Secret:
1. Go to your GitHub repository -> **Settings** -> **Secrets and variables** -> **Actions**.
2. Click **New repository secret**.
3. Name: `ORACLE_VM_SSH_KEY`.
4. Value: Paste your private SSH key (`id_rsa` or Oracle `.key` file content).
5. Now, every `git push origin main` will automatically update the code and restart the service!

---

## 🔍 Verification & Diagnostics Checklist

| Check | Command | Expected Output |
| :--- | :--- | :--- |
| **Django Service** | `sudo systemctl status genai.service` | `Active: active (running)` |
| **Local Port 8080** | `curl -I http://127.0.0.1:8080/chat/` | `HTTP/1.1 200 OK` |
| **Nginx Status** | `sudo systemctl status nginx` | `Active: active (running)` |
| **Nginx Config** | `sudo nginx -t` | `syntax is ok / test is successful` |
| **Public HTTPS** | `curl -I https://genaisample.duckdns.org/chat/` | `HTTP/2 200` |

---

## ❓ Troubleshooting Quick Reference

* **502 Bad Gateway:**
  * Django is not running on port 8080.
  * Check logs: `sudo journalctl -u genai.service -e`.
  * Ensure virtualenv path in `genai.service` matches `/home/opc/GENAI/venv/bin/python3`.
* **400 Bad Request (Invalid HTTP_HOST header):**
  * `ALLOWED_HOSTS` in `config/settings.py` or `.env` doesn't include `genaisample.duckdns.org`.
  * Set `ALLOWED_HOSTS=genaisample.duckdns.org,129.225.111.80,localhost,127.0.0.1,*` in `.env` and restart `genai.service`.
* **Connection Timed Out:**
  * OCI Security List Ingress Rule for Port 80/443 is missing, or OS `firewalld` is blocking incoming connections. See Step 5.
