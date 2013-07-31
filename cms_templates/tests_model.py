from django.db import models
from cms.models import CMSPlugin
from dbtemplates.models import Template
from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool


class PluginModelA(CMSPlugin):
    some_template = models.ForeignKey(Template, blank=True, null=True)


class PluginModelB(CMSPlugin):
    some_template_name = models.CharField(max_length=100)


class PluginModelC(CMSPlugin):
    templ_name = models.CharField(max_length=100)


class PluginModelD(CMSPlugin):
    templ_name = models.CharField(max_length=100)


class PluginBaseA(CMSPluginBase):
    model = PluginModelA
    name = "Plugin A"

    @classmethod
    def get_templates(cls, site, **kwargs):
        return cls.model.objects.filter(
            placeholder__page__site=site, some_template__isnull=False).\
            values_list('some_template__name', flat=True).distinct()


class PluginBaseB(CMSPluginBase):
    model = PluginModelB
    name = "Plugin B"

    @classmethod
    def get_templates(cls, site, **kwargs):
        return cls.model.objects.filter(
            placeholder__page__site=site, some_template_name__isnull=False).\
            values_list('some_template_name', flat=True).distinct()


class PluginBaseC(CMSPluginBase):
    model = PluginModelC
    name = "Plugin C"


class PluginBaseD(CMSPluginBase):
    model = PluginModelD
    name = "Plugin D"


plugin_pool.register_plugin(PluginBaseA)
plugin_pool.register_plugin(PluginBaseB)
plugin_pool.register_plugin(PluginBaseC)
plugin_pool.register_plugin(PluginBaseD)
