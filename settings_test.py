INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.sitemaps',
    'cms',
    'mptt',
    'menus',
    'south',
    'sekizai',
    'dbtemplates',
    'cms_templates',
    'django_nose',
]

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
CMS_TEMPLATES = []
CMS_MODERATOR = True
CMS_PERMISSION = True
STATIC_ROOT = '/static/'
STATIC_URL = '/static/'
ROOT_URLCONF = 'pbs_test_runner'
TEMPLATE_CONTEXT_PROCESSORS = [
    "django.contrib.auth.context_processors.auth",
    'django.contrib.messages.context_processors.messages',
    "django.core.context_processors.i18n",
    "django.core.context_processors.debug",
    "django.core.context_processors.request",
    "django.core.context_processors.media",
    'django.core.context_processors.csrf',
    "cms.context_processors.media",
    "sekizai.context_processors.sekizai",
    "django.core.context_processors.static",
]
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME' : '/tmp/bento.db', # Or path to database file if using sqlite3.
        'USER' : '', # Not used with sqlite3.
        'PASSWORD' : '', # Not used with sqlite3.
        'HOST' : '', # Set to empty string for localhost. Not used with sqlite3.
        'PORT' : '', # Set to empty string for default. Not used with sqlite3.
    }
}
MIDDLEWARE_CLASSES = (
    'django.middleware.cache.UpdateCacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',

        'cms_templates.middleware.SiteIDPatchMiddleware',
    'cms_templates.middleware.DBTemplatesMiddleware',

        'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',

        # djangos-cms specific
    # Not using multilingual fixes the login bug caused by dynamic site-id hack
    # 'cms.middleware.multilingual.MultilingualURLMiddleware',
    'cms.middleware.page.CurrentPageMiddleware',
    'cms.middleware.user.CurrentUserMiddleware',
    'cms.middleware.toolbar.ToolbarMiddleware',
    # for basic http auth
    # 'multisiteauth.middleware.BasicAuthProtectionMiddleware',
    # 'django.middleware.cache.FetchFromCacheMiddleware',
)
