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


class PluginBaseA(CMSPluginBase):
    model = PluginModelA
    name = "Plugin A"

    @staticmethod
    def get_template_field_name():
        return 'some_template'


class PluginBaseB(CMSPluginBase):
    model = PluginModelB
    name = "Plugin B"

    @staticmethod
    def get_template_field_name():
        return 'some_template_name'


class PluginBaseC(CMSPluginBase):
    model = PluginModelC
    name = "Plugin C"


plugin_pool.register_plugin(PluginBaseA)
plugin_pool.register_plugin(PluginBaseB)
plugin_pool.register_plugin(PluginBaseC)
