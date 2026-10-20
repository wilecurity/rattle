<div align="center">
  <h1>🐍 Rattle</h1>
  <p><strong>Google OAuth Consent Phishing Toolkit</strong></p>
  <p>
    <img src="https://img.shields.io/badge/version-1.1.0-blue" alt="Version">
    <img src="https://img.shields.io/badge/python-3.8+-green" alt="Python">
    <img src="https://img.shields.io/badge/license-MIT-red" alt="License">
    <img src="https://img.shields.io/badge/platform-linux-lightgrey" alt="Platform">
  </p>
  <p><i>Professional-grade OAuth consent phishing framework with a full Gmail Client, Email Campaigns, and SMTP integration</i></p>
</div>

---

## 📋 Overview

**Rattle** is a complete, GUI-driven toolkit for Google OAuth consent phishing. It provides a professional dashboard to create campaigns, capture OAuth tokens, and manage victims. The **OAuth Viewer** is a fully functional Gmail Client that lets you read, send, reply, forward, delete, and manage emails using captured tokens. **Email Campaigns** let you send phishing lures directly from the panel via SMTP.

> ⚠️ **Disclaimer**: This tool is for educational and authorized security testing purposes only. Unauthorized use is illegal. The author assumes no responsibility for misuse.

---

## ✨ Features

### Core Features
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

### 🆕 New in v1.1 — OAuth Viewer (Gmail Client)

The OAuth Viewer is a **full-featured, dark-themed Gmail desktop client** that uses captured OAuth tokens to access the victim's mailbox.

| Feature | Description |
|---------|-------------|
| 👁️ **Full Email Client** | Professional dark-themed GUI with folder navigation |
| 📥 **Folder Access** | Inbox, Starred, Sent, Drafts, Trash, Spam, All Mail |
| 🏷 **Label Management** | View and filter by custom Gmail labels |
| 📖 **Read Emails** | Full message rendering with headers and body |
| ✏️ **Compose** | Send new emails directly from the client |
| ↩️ **Reply** | Reply to any email with proper threading |
| ↪️ **Forward** | Forward emails with original content |
| ⭐ **Star/Unstar** | Toggle star status on messages |
| 📩 **Read/Unread** | Toggle read status |
| 🗑️ **Delete** | Move emails to Trash |
| 🔍 **Search** | Full Gmail search syntax support |
| 📎 **Attachments** | View and download email attachments |
| 🔄 **Auto Token Refresh** | Automatically refreshes access tokens on 401 errors |
| 🌙 **Dark Theme** | Professional, easy-on-the-eyes dark interface |

### 🆕 New in v1.1 — Email Campaigns

Send phishing lures directly from Rattle using SMTP.

| Feature | Description |
|---------|-------------|
| 📤 **Email Campaigns** | Send emails to target lists automatically |
| 📄 **Email Templates** | Create reusable HTML templates with placeholders |
| ⚙️ **SMTP Settings** | Configure and test SMTP servers in the panel |
| 📬 **Background Sending** | Emails sent in background threads |
| 🎯 **Target Tracking** | Track individual targets (pending, sent, failed) |
| 🔄 **Placeholder Variables** | Use `{{name}}`, `{{email}}`, `{{link}}` in templates |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Google Cloud Console project with OAuth credentials
- Domain name with DNS configured
- VPS (Ubuntu 20.04/22.04/24.04 recommended)
- Tkinter (for OAuth Viewer): `sudo apt install python3-tk`

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
   - Add required scopes:
     - `openid`
     - `profile`
     - `email`
     - `https://www.googleapis.com/auth/gmail.readonly`
     - `https://www.googleapis.com/auth/gmail.send`
     - `https://www.googleapis.com/auth/gmail.modify`
   - Add yourself as a test user
   - Create OAuth Client ID (Web application)
   - Add redirect URI: `https://yourdomain.com/callback`

2. **Configure the app**:
   ```bash
   # Edit app.py with your credentials
   nano app.py
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

---

## 🎯 Usage

### 1. Creating a Campaign

1. Navigate to **Campaigns** > **Create Campaign**
2. Enter your Google Client ID and Client Secret
3. Set the redirect URI (must match Google Cloud Console)
4. Select the scopes you want to request
5. Generate the phishing link

### 2. Capturing Tokens

1. Send the phishing link to the target
2. Target authenticates via Google
3. OAuth token is captured automatically
4. View captured tokens in the **Tokens** section

### 3. Using the OAuth Viewer (Gmail Client)

The OAuth Viewer is a **desktop Gmail client** that uses captured tokens.

**Launch it**:
```bash
python3 oauth_viewer.py
```

**Connect**:
1. Paste the **Access Token** from Rattle
2. Paste the **Refresh Token** (recommended for auto-refresh)
3. Click **Connect**

**Features available**:
| Action | How |
|--------|-----|
| **Read emails** | Click any email in the list |
| **Switch folders** | Click Inbox, Sent, Drafts, etc. in sidebar |
| **Filter by label** | Click a label in the sidebar |
| **Search** | Type in the search bar and press Enter |
| **Compose** | Click the green "Compose" button |
| **Reply** | Click "Reply" in the viewer toolbar |
| **Forward** | Click "Forward" in the viewer toolbar |
| **Star/Unstar** | Click "Star" in the viewer toolbar |
| **Mark unread** | Click "Unread" in the viewer toolbar |
| **Delete** | Click "Delete" in the viewer toolbar |
| **Download attachment** | Click the attachment button in the email |

**Token Refresh**:
- If you provided a refresh token, the client automatically refreshes expired access tokens
- You can also update the token manually in the toolbar

### 4. Sending Email Campaigns

1. **Configure SMTP**:
   - Go to **Email** > **SMTP Settings**
   - Click **Add SMTP**
   - Enter your SMTP details (host, port, username, password)
   - Click **Test** to verify

2. **Create a Template**:
   - Go to **Email** > **Templates**
   - Click **New Template**
   - Enter name, subject, and HTML body
   - Use placeholders: `{{name}}`, `{{email}}`, `{{link}}`

3. **Create an Email Campaign**:
   - Go to **Email** > **Email Campaigns**
   - Click **New Email Campaign**
   - Select your phishing campaign, template, and SMTP
   - Paste target emails (one per line: `email,name`)
   - Click **Create**

4. **Send Emails**:
   - Open the campaign
   - Click **Start Sending**
   - Emails are sent in the background
   - Track progress in real-time

### 5. Using Captured Tokens via CLI

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
├── app.py                 # Main Flask application (ALL models & routes)
├── oauth_viewer.py        # OAuth Viewer (Full Gmail Client)
├── requirements.txt       # Python dependencies
├── setup_nginx_ssl.sh     # Nginx + SSL automation
├── static/
│   ├── css/
│   │   └── style.css      # Custom styles
│   └── js/
│       └── app.js         # Frontend JavaScript
└── templates/
    ├── base.html          # Base template with navigation
    ├── login.html         # Login page
    ├── dashboard.html     # Main dashboard
    ├── campaigns.html     # Campaign management
    ├── campaign_create.html
    ├── campaign_detail.html
    ├── victims.html       # Victim list
    ├── tokens.html        # Token management
    ├── settings.html      # Settings page
    ├── smtp_list.html     # SMTP configurations
    ├── smtp_form.html     # Add SMTP
    ├── template_list.html # Email templates
    ├── template_form.html # Create template
    ├── email_campaigns.html    # Email campaigns list
    ├── email_campaign_form.html # Create email campaign
    └── email_campaign_detail.html # Email campaign details
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

### Web App (Rattle)
- Python 3.8+
- Flask 2.3+
- SQLAlchemy 2.0+
- Gunicorn (production)
- Nginx (production)
- Certbot (SSL)

### OAuth Viewer (Gmail Client)
- Python 3.8+
- Tkinter (`sudo apt install python3-tk`)
- `requests`
- `email` (built-in)

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

<div align="center">
  <sub>Built with ❤️ for security research</sub>
</div>
