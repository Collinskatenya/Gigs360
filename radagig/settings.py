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
    
    # Third Party Apps
    'django_daraja',  # For M-Pesa Integration
    
    # My Apps
    'core',           # Handles Custom User & Auth
    'inventory',      # Handles Gear & QR Codes
    'events',         # Handles Gigs & PDF Invoicing
    'finance',        # Handles Transactions (Future)
    'community',      # Handles GigHub (Future)
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
                
                # 🚨 CRITICAL ADDITION FOR NOTIFICATIONS 🚨
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
STATIC_URL = 'static/'
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

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'