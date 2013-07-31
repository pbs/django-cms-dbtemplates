from django.conf import settings

shared_sites = getattr(settings, 'DBTEMPLATES_SHARED_SITES', [])
include_orphan = getattr(settings, 'DBTEMPLATES_INCLUDE_ORPHAN', False)
restrict_user = getattr(settings, 'DBTEMPLATES_RESTRICT_USER', False)

"""
    This is a list of ('Plugin') tuples, where 'Plugin'
    is a CMSPluginBase derivative and registered in cms plugin pool.

    The Plugin class must define 'get_templates' class method like
    in the example below.

    The 'site' parameter is mandatory.
    The return type should be a list/queryset.
    The templates returned can then be used in the validation process.

    class Plugin(CMSPluginBase):
        model = PluginModel
        ...

        @classmethod
        def get_templates(cls, site, **kwargs):
            pages = site.page_set.all()
            return cls.model.objects.filter(placeholder__page__in=pages).\
                values_list('template__name', flat=True).distinct()

   For an example on how to configure this see settings_test.py and
        tests_models.py
"""

PLUGIN_TEMPLATE_REFERENCES = []
