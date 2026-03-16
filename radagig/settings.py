from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-xdo#q5cz=5y&a5f*0zb*t-hao*_ss6ktf+fgq4b0_dhg!7t#@z'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# -------------------------------------------------------------------------
# APPLICATION DEFINITION
# -------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # CRITICAL FIX: Added humanize to fix the Staff Dashboard TemplateSyntaxError
    'django.contrib.humanize',
    
    # Third Party Apps
    # 'django_daraja',  # <--- UNCOMMENT when you install django-daraja and build finance app
    
    # My Apps
    'core',           # Handles Custom User & Auth
    'inventory',      # Handles Gear & QR Codes
    'events',         # Handles Gigs & PDF Invoicing
    
    # ⚠️ These apps don't exist yet. Keeping them active would crash the server.
    # Uncomment them only after you run 'python manage.py startapp finance', etc.
     'finance', 
     'galleries',       
     'community',      
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # 🚨 INJECTED: The Asymmetric Presence Tracker Engine
    'core.middleware.ActiveUserMiddleware',
]

ROOT_URLCONF = 'radagig.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],  # Looks for templates in root folder
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                
                # 🚨 GLOBAL NOTIFICATIONS (Verified)
                'core.context_processors.notifications', 
            ],
        },
    },
]

WSGI_APPLICATION = 'radagig.wsgi.application'

# -------------------------------------------------------------------------
# DATABASE
# -------------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# -------------------------------------------------------------------------
# AUTHENTICATION
# -------------------------------------------------------------------------
# Critical: Tells Django to use your custom user model in the 'core' app
AUTH_USER_MODEL = 'core.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Login / Logout Redirects
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'home'

# -------------------------------------------------------------------------
# INTERNATIONALIZATION
# -------------------------------------------------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True

# -------------------------------------------------------------------------
# STATIC & MEDIA FILES (Critical for PDF Engine & QR Codes)
# -------------------------------------------------------------------------
# 🚨 FIX APPLIED: Added leading slash to resolve absolute paths for xhtml2pdf
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media Files (User Uploads: Logos, Profile Pics, Generated PDFs)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# -------------------------------------------------------------------------
# DEVELOPMENT SECURITY SETTINGS
# -------------------------------------------------------------------------
# Fixes 403 Forbidden Error during development
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_HTTPONLY = False

# Email (Console Backend for testing - prints emails to terminal)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'Gigs360 <noreply@gigs360.co.ke>'

# 💳 M-PESA DARAJA API CONFIGURATION (Future Use)
# -------------------------------------------------------------------------
# These are the Sandbox (Test) Credentials.
# When you go live, change ENVIRONMENT to 'production' and update keys.
MPESA_ENVIRONMENT = 'sandbox' 
MPESA_CONSUMER_KEY = 'your_consumer_key_here'      
MPESA_CONSUMER_SECRET = 'your_consumer_secret_here' 
MPESA_SHORTCODE = '174379' # Standard Test Paybill
MPESA_PASSKEY = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'
MPESA_CALLBACK_URL = 'https://your-domain.com/finance/callback/' 

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==========================================
# 📦 INVENTORY LIMITS
# ==========================================
INVENTORY_LIMITS = {
    'FREE': 20,
    'PRO': 100,
    'ENTERPRISE': float('inf') # Infinite
}

# ==========================================
# 🌍 EXTERNAL SERVICES
# ==========================================
# TEMPORARY FIX: Hardcoding the key to force it to work.
# We will move this back to .env later.

GOOGLE_MAPS_API_KEY = 'AIzaSyAhx9g5jRBP76GEsW4St9Jfywa9cgwe03c'