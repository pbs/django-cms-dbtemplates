import unittest

custom_settings = {
    'INSTALLED_APPS': [
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
    ],
    'CMS_TEMPLATES': [],
    'CMS_MODERATOR': True,
    'CMS_PERMISSION': True,
    'STATIC_ROOT': '/static/',
    'STATIC_URL': '/static/',
    'ROOT_URLCONF': 'pbs_test_runner',
    'TEMPLATE_CONTEXT_PROCESSORS': [
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
    ],
    'DATABASES': {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': '/tmp/bento.db',
            'USER': '',
            'PASSWORD': '',
            'HOST': '',
            'PORT': '',
        }
    },
    'MIDDLEWARE_CLASSES':  (
        'django.middleware.cache.UpdateCacheMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',

        'cms_templates.middleware.SiteIDPatchMiddleware',
        'cms_templates.middleware.DBTemplatesMiddleware',

        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',

        'cms.middleware.page.CurrentPageMiddleware',
        'cms.middleware.user.CurrentUserMiddleware',
        'cms.middleware.toolbar.ToolbarMiddleware',
        # for basic http auth
        # 'multisiteauth.middleware.BasicAuthProtectionMiddleware',
        # 'django.middleware.cache.FetchFromCacheMiddleware',
    ),
}

urlpatterns = []

class DjangoTestCase(unittest.TestCase):
    def setUp(self):
        self.settings = _setup_settings()
        # ugly hack to get arround imports cycle ( settings needs to be
        # configured to be able to use other django imports)
        global urlpatterns
        urlpatterns = _url_patterns()

    def test_django(self):
        from django.test.utils import get_runner
        DjangoTestRunner = get_runner(self.settings)
        runner = DjangoTestRunner(
            verbosity=2, interactive=False, failfast=False)
        failures = runner.run_tests(["cms_templates"])
        self.assertEqual(failures, 0)


class NoseTestCase(unittest.TestCase):
    def setUp(self):
        global custom_settings
        custom_settings["INSTALLED_APPS"].append("django_nose")
        custom_settings["TEST_RUNNER"] = "django_nose.NoseTestSuiteRunner"
        self.settings = _setup_settings()
        # ugly hack to get arround imports cycle ( settings needs to be
        # configured to be able to use other django imports)
        global urlpatterns
        urlpatterns = _url_patterns()

    def test_nose_django(self):
        from django_nose import NoseTestSuiteRunner
        runner = NoseTestSuiteRunner(verbosity=2, interactive=False)
        failures = runner.run_tests(["cms_templates"])
        self.assertEqual(failures, 0)


def _setup_settings():
    from django.conf import settings
    settings.configure(**custom_settings)
    from south.management.commands import patch_for_test_db_setup
    patch_for_test_db_setup()
    from django.contrib import admin
    admin.autodiscover()
    return settings


def _url_patterns():
    from django.conf.urls.defaults import patterns, url, include
    from django.contrib import admin
    return patterns('', url(r'^admin/', include(admin.site.urls)))