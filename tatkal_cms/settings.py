import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'tatkal-cms-secret-key-2024-university-management-system'
DEBUG = True
ALLOWED_HOSTS = ['*']

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

# :::comment::: Gmail SMTP – set GMAIL_HOST_USER and GMAIL_APP_PASSWORD env vars.
# With real credentials (Gmail 2FA + App Password) emails are delivered via SMTP.
# Without them, OTPs are printed to the console for local development.
_gmail_user     = os.environ.get('GMAIL_HOST_USER', 'tatkalservice07@gmail.com')
_gmail_password = os.environ.get('GMAIL_APP_PASSWORD', 'rksk thja isiq sqkl')

if _gmail_user and _gmail_password:
    EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST          = 'smtp.gmail.com'
    EMAIL_PORT          = 587
    EMAIL_USE_TLS       = True
    EMAIL_HOST_USER     = _gmail_user
    EMAIL_HOST_PASSWORD = _gmail_password
    DEFAULT_FROM_EMAIL  = f'Tatkal CMS <{_gmail_user}>'
else:
    # :::comment::: Dev fallback – OTPs appear in the runserver console
    EMAIL_BACKEND      = 'django.core.mail.backends.console.EmailBackend'
    EMAIL_HOST_USER    = 'noreply@tatkal.local'
    DEFAULT_FROM_EMAIL = 'Tatkal CMS <noreply@tatkal.local>'

# Twilio SMS OTP configuration
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', '')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '')

# Multi-University Configuration
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

# Default University (can be overridden per student)
DEFAULT_UNIVERSITY = 'jntu_hyd'
UNIVERSITY_NAME = UNIVERSITIES[DEFAULT_UNIVERSITY]['name']
UNIVERSITY_ADDRESS = UNIVERSITIES[DEFAULT_UNIVERSITY]['address']
UNIVERSITY_LOGO = UNIVERSITIES[DEFAULT_UNIVERSITY]['logo']

RAZORPAY_KEY_ID = 'rzp_test_demo_key'
RAZORPAY_KEY_SECRET = 'demo_secret'

NORMAL_FEE = {
    'bonafide': 50, 'study': 50, 'transfer': 500, 'course_completion': 100,
    'medium': 50, 'provisional': 200, 'migration': 300, 'income': 50,
    'internship': 100, 'character': 50
}
TATKAL_MULTIPLIER = 3

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

# Template tag libraries
# In templates, use {% load cert_tags %}

# ─── Logging ──────────────────────────────────────────────────────────────────
# Prints INFO+ from the certificates app (including email send/fail) to console.
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

# ─── Session Persistence (Fix: users stay logged in) ──────────────────────────
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14          # 14 days
SESSION_EXPIRE_AT_BROWSER_CLOSE = False           # survive browser restart
SESSION_SAVE_EVERY_REQUEST = True                 # refresh expiry on activity
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# ─── Authentication Backends (Fix: login(request, user) without backend error) ─
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]
