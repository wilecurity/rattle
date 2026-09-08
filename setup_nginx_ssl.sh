#!/bin/bash

# ============================================
#  Nginx + SSL Setup Script
# For Rattle or any Flask app
# ============================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[*]${NC} $1"; }
print_success() { echo -e "${GREEN}[+]${NC} $1"; }
print_error() { echo -e "${RED}[!]${NC} $1"; }

# Check root
if [ "$EUID" -ne 0 ]; then 
    print_error "Please run as root (use sudo)"
    exit 1
fi

clear
echo ""
echo "=========================================="
echo -e "${GREEN}Nginx + SSL Setup${NC}"
echo "=========================================="
echo ""

# Get domain
read -p "Enter your domain (e.g., rattle.yourdomain.com): " DOMAIN

if [ -z "$DOMAIN" ]; then
    print_error "Domain cannot be empty"
    exit 1
fi

# Get email
read -p "Enter your email for Let's Encrypt: " EMAIL

if [ -z "$EMAIL" ]; then
    EMAIL="admin@$DOMAIN"
    print_status "Using: $EMAIL"
fi

# Get project path
read -p "Enter project path [~/rattle]: " PROJECT_PATH

if [ -z "$PROJECT_PATH" ]; then
    PROJECT_PATH="$HOME/rattle"
fi

# ============================================
# Install Nginx & Certbot
# ============================================

print_status "Installing Nginx, Certbot, and Python3-certbot-nginx..."

apt update -qq
apt install -y -qq nginx certbot python3-certbot-nginx

print_success "Nginx and Certbot installed"

# ============================================
# Configure Nginx
# ============================================

print_status "Configuring Nginx..."

cat > /etc/nginx/sites-available/rattle << 'EOF'
server {
    listen 80;
    server_name DOMAIN_PLACEHOLDER;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name DOMAIN_PLACEHOLDER;

    ssl_certificate /etc/letsencrypt/live/DOMAIN_PLACEHOLDER/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/DOMAIN_PLACEHOLDER/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias PROJECT_PATH_PLACEHOLDER/static/;
        expires 1y;
    }

    access_log /var/log/nginx/rattle_access.log;
    error_log /var/log/nginx/rattle_error.log;
}
EOF

# Replace placeholders
sed -i "s/DOMAIN_PLACEHOLDER/$DOMAIN/g" /etc/nginx/sites-available/rattle
sed -i "s|PROJECT_PATH_PLACEHOLDER|$PROJECT_PATH|g" /etc/nginx/sites-available/rattle

# Enable site
rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/rattle /etc/nginx/sites-enabled/

print_success "Nginx configured"

# ============================================
# Get SSL Certificate
# ============================================

print_status "Obtaining SSL certificate..."

# Stop nginx for standalone
systemctl stop nginx

certbot certonly --standalone -d "$DOMAIN" --email "$EMAIL" --agree-tos --no-eff-email --non-interactive

if [ $? -eq 0 ]; then
    print_success "SSL certificate obtained"
else
    print_error "Certificate failed. Trying webroot..."
    
    mkdir -p /var/www/html
    certbot certonly --webroot -w /var/www/html -d "$DOMAIN" --email "$EMAIL" --agree-tos --no-eff-email --non-interactive
    
    if [ $? -ne 0 ]; then
        print_error "SSL failed. Check DNS and try again."
        systemctl start nginx
        exit 1
    fi
fi

# Start nginx
systemctl start nginx
systemctl enable nginx

print_success "Nginx started with SSL"

# ============================================
# Auto-renewal
# ============================================

print_status "Setting up auto-renewal..."

systemctl enable certbot.timer
systemctl start certbot.timer

print_success "Auto-renewal enabled"

# ============================================
# Done
# ============================================

echo ""
echo "=========================================="
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "  Domain: https://$DOMAIN"
echo "  Nginx: /etc/nginx/sites-available/rattle"
echo "  SSL: /etc/letsencrypt/live/$DOMAIN/"
echo ""
echo "  Next steps:"
echo "  1. Update Google Cloud Console:"
echo "     - JavaScript origins: https://$DOMAIN"
echo "     - Redirect URI: https://$DOMAIN/callback"
echo ""
echo "  2. Run your Flask app:"
echo "     cd $PROJECT_PATH"
echo "     gunicorn -w 4 -b 127.0.0.1:8000 app:app"
echo ""
echo "  SSL renews automatically via certbot timer."
echo "=========================================="
