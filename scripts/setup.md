# 🚀 Server Deployment & Setup Guide

---

## 📋 Step 1: VM Prerequisites & Initial Setup

### 1. Install System Dependencies (Git & Python)
```bash
sudo dnf install -y git python3 python3-pip
```
*(On Ubuntu/Debian: `sudo apt update && sudo apt install -y git python3 python3-venv python3-pip`)*

---

### 2. Clone the Repository
```bash
cd /home/opc
git clone https://github.com/viswavisan/GENAI.git
cd /home/opc/GENAI
```

---

### 3. Create Virtual Environment & Install Requirements
```bash
python3 -m venv /home/opc/GENAI/venv
source /home/opc/GENAI/venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### Test Project Execution
```bash
/home/opc/GENAI/venv/bin/python3 /home/opc/GENAI/manage.py runserver 0.0.0.0:8080
```

---

### 4. Create the Production `.env` File under Secret Directory
Create directory `/home/opc/secret` (outside git repo) and create `.env`:
```bash
mkdir -p /home/opc/secret
nano /home/opc/secret/.env
```

Add your production configuration:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
UNIVERSAL_AGENT_PASSWORD=your_secure_password_here
OLLAMA_BASE_URL=http://localhost:11434
DEBUG=True
ALLOWED_HOSTS=genaisample.duckdns.org,129.225.111.80,localhost,127.0.0.1
```
*(Save with `Ctrl+O`, press `Enter`, then exit with `Ctrl+X`)*

Restrict permissions to ensure only user `opc` can read it:
```bash
chmod 600 /home/opc/secret/.env
```

---

## ⚙️ Step 2: Systemd Service Setup (`genai.service`)

The systemd service keeps your Django application running 24/7 in the background and restarts it automatically on system reboots or crashes.

### 1. Copy the Service File
```bash
sudo cp /home/opc/GENAI/scripts/genai.service /etc/systemd/system/genai.service
```

### 2. Verify Service File Contents
```bash
nano /etc/systemd/system/genai.service
```

### 3. Reload, Enable & Start the Service
```bash
sudo systemctl daemon-reload
sudo systemctl enable genai.service
sudo systemctl start genai.service
sudo systemctl status genai.service
```

### 🛠️ Useful Service Management Commands
```bash
# View live application logs
sudo journalctl -u genai.service -f

# Restart service after code updates
sudo systemctl restart genai.service

# Stop service
sudo systemctl stop genai.service
```

---

## 🌐 Step 3: Nginx Reverse Proxy Setup (`genai.conf`)

Nginx routes public incoming requests from `genaisample.duckdns.org` on port 80/443 to the internal Django service running on `127.0.0.1:8080`.

### 1. Install Nginx & Place Configuration
On Oracle Linux / RHEL:
```bash
sudo dnf install -y nginx
sudo cp /home/opc/GENAI/scripts/genai.conf /etc/nginx/conf.d/genai.conf
```

### 2. Open Firewall for Ports 80 & 443
```bash
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --reload
```

### 3. Test Configuration & Start Nginx
```bash
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx
```

---

## 🔒 Step 4: Install Certbot & Enable HTTPS (Port 443)

### 1. Enable EPEL Repository & Install Certbot
```bash
sudo dnf install -y epel-release
sudo pip3 install certbot certbot-nginx
sudo ln -s /usr/local/bin/certbot /usr/bin/certbot
/usr/local/bin/certbot --version
```

### 2. Generate SSL Certificate for Domain
Once your domain `genaisample.duckdns.org` points to `129.225.111.80` and Nginx is running:

```bash
sudo /usr/local/bin/certbot --nginx -d genaisample.duckdns.org
```

Certbot will:
1. Verify domain ownership via HTTP (port 80).
2. Generate SSL certificates under `/etc/letsencrypt/live/genaisample.duckdns.org/`.
3. Automatically configure port 443 SSL in `/etc/nginx/conf.d/genai.conf` and redirect HTTP to HTTPS.
4. Reload Nginx.

### 3. Verify Certificate Auto-Renewal
```bash
sudo /usr/local/bin/certbot renew --dry-run
```

---

## 🛡️ Step 5: Permissions & SELinux Troubleshooting

If the service fails to start or gives permission errors, run the following diagnostic and resolution steps:

### 1. Ensure Correct File Permissions & Ownership
```bash
sudo chmod 755 /home/opc/GENAI/manage.py
sudo chmod 755 /home/opc/GENAI/venv/bin/python
sudo chmod 755 /home/opc/GENAI/venv/bin/python3
sudo chmod 755 /home/opc/GENAI/venv/bin/python3.9
sudo chown opc:opc /home/opc/GENAI/venv/bin/python*
```

### 2. Inspect Error Logs
```bash
journalctl -u genai.service -e
```

### 3. Check and Resolve SELinux Restrictions
Check current SELinux status:
```bash
getenforce
```

Temporarily set SELinux to Permissive mode to test:
```bash
sudo setenforce 0
sudo systemctl restart genai.service
```

If the service starts successfully in permissive mode, SELinux is blocking execution. Generate and install an SELinux policy module to permanently allow it:
```bash
sudo ausearch -c 'python3' --raw | audit2allow -M my-python
sudo semodule -i my-python.pp
```
*(Repeat once more if additional policies are reported)*
