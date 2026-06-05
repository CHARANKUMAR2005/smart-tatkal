import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-in-production')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = [h.strip() for h in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]

# Render automatically injects RENDER_EXTERNAL_HOSTNAME — add it without any dashboard config.
RENDER_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '')
if RENDER_HOSTNAME and RENDER_HOSTNAME not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(RENDER_HOSTNAME)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'accounts',
    'certificates',
    'payments',
    'notifications',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'tatkal_cms.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'tatkal_cms.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'tatkal_cms.db',
    }
}

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ALLOW_ALL_ORIGINS = True

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
}

# ─── App base URL ─────────────────────────────────────────────────────────────
# Falls back to RENDER_EXTERNAL_HOSTNAME when BASE_URL is not explicitly set.
_render_base = f'https://{RENDER_HOSTNAME}' if RENDER_HOSTNAME else ''
BASE_URL = os.environ.get('BASE_URL', _render_base or 'http://localhost:8000').rstrip('/')

# ─── CSRF trusted origins ─────────────────────────────────────────────────────
# Collect all non-localhost origins that need to POST to this app.
CSRF_TRUSTED_ORIGINS = []
if BASE_URL and not BASE_URL.startswith('http://localhost'):
    CSRF_TRUSTED_ORIGINS.append(BASE_URL)
if _render_base and _render_base != BASE_URL:
    CSRF_TRUSTED_ORIGINS.append(_render_base)

# ─── HTTPS proxy header (Render / most cloud platforms terminate SSL) ─────────
# Lets Django know the original request was HTTPS even though gunicorn sees HTTP.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ─── University branding ──────────────────────────────────────────────────────
UNIVERSITY_NAME    = os.environ.get('UNIVERSITY_NAME', 'Kakatiya University')
UNIVERSITY_ADDRESS = os.environ.get('UNIVERSITY_ADDRESS', 'Warangal, Telangana - 506009')
UNIVERSITY_LOGO    = os.environ.get('UNIVERSITY_LOGO', 'images/logo.png')
SUPPORT_EMAIL      = os.environ.get('SUPPORT_EMAIL', '')

# ─── Gmail SMTP ───────────────────────────────────────────────────────────────
# Set GMAIL_HOST_USER and GMAIL_APP_PASSWORD in .env (Gmail 2FA + App Password).
# When both are blank, OTPs/emails are printed to the console (local dev).
_gmail_user     = os.environ.get('GMAIL_HOST_USER', '')
_gmail_password = os.environ.get('GMAIL_APP_PASSWORD', '')

if _gmail_user and _gmail_password:
    EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST          = 'smtp.gmail.com'
    EMAIL_PORT          = 587
    EMAIL_USE_TLS       = True
    EMAIL_HOST_USER     = _gmail_user
    EMAIL_HOST_PASSWORD = _gmail_password
    DEFAULT_FROM_EMAIL  = f'Tatkal CMS <{_gmail_user}>'
else:
    EMAIL_BACKEND      = 'django.core.mail.backends.console.EmailBackend'
    EMAIL_HOST_USER    = 'noreply@tatkal.local'
    DEFAULT_FROM_EMAIL = 'Tatkal CMS <noreply@tatkal.local>'

# Fill SUPPORT_EMAIL from the sender address if not set explicitly
if not SUPPORT_EMAIL:
    SUPPORT_EMAIL = _gmail_user or 'noreply@tatkal.local'

# ─── Twilio SMS OTP (optional) ────────────────────────────────────────────────
TWILIO_ACCOUNT_SID  = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN   = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')

# ─── Multi-University Configuration ──────────────────────────────────────────
UNIVERSITIES = {
    'jntu_hyd': {
        'name': 'JNTU Hyderabad',
        'address': 'Kukatpally, Hyderabad, Telangana - 500085',
        'logo': 'images/logo.png',
    },
    'jntu_kak': {
        'name': 'JNTU Kakinada',
        'address': 'Kakinada, Andhra Pradesh - 533003',
        'logo': 'images/logo.png',
    },
    'jntu_ana': {
        'name': 'JNTU Anantapur',
        'address': 'Anantapur, Andhra Pradesh - 515002',
        'logo': 'images/logo.png',
    },
    'private': {
        'name': 'Private University',
        'address': 'Hyderabad, Telangana',
        'logo': 'images/logo.png',
    },
}

# ─── Payment Gateway ──────────────────────────────────────────────────────────
RAZORPAY_KEY_ID     = os.environ.get('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '')

# ─── Certificate Fees ─────────────────────────────────────────────────────────
NORMAL_FEE = {
    'bonafide': 50, 'study': 50, 'transfer': 500, 'course_completion': 100,
    'medium': 50, 'provisional': 200, 'migration': 300, 'income': 50,
    'internship': 100, 'character': 50
}
TATKAL_MULTIPLIER = 3

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

# ─── Logging ──────────────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {'format': '[%(levelname)s %(name)s] %(message)s'},
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'certificates': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.core.mail': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# ─── Session Persistence ──────────────────────────────────────────────────────
SESSION_COOKIE_AGE            = 60 * 60 * 24 * 14
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST    = True
SESSION_ENGINE                = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_HTTPONLY       = True
SESSION_COOKIE_SAMESITE       = 'Lax'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]
