import os
import sys
import unittest
from os.path import dirname, abspath
from optparse import OptionParser

sys.path.insert(0, dirname(abspath(__file__)))

from django.conf import settings
if not settings.configured:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'settings_test'

from django_nose import NoseTestSuiteRunner


def runtests(*test_args, **kwargs):
    if 'south' in settings.INSTALLED_APPS:
        from south.management.commands import patch_for_test_db_setup
        patch_for_test_db_setup()

    if not test_args:
        test_args = ['cms_templates.tests']

    kwargs.setdefault('interactive', False)

    test_runner = NoseTestSuiteRunner(**kwargs)
    failures = test_runner.run_tests(test_args)

    class TestWrapper(unittest.TestCase):
        def setUp(self):
            pass
        def runTest(self):
            self.assertEqual(failures, 0)

    return TestWrapper()

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('--verbosity', dest='verbosity', action='store',
                      default=1, type=int)
    parser.add_options(NoseTestSuiteRunner.options)
    (options, args) = parser.parse_args()
    runtests(*args, **options.__dict__)
