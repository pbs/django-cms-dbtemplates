from django.db.models import signals
from django.core.cache import cache

from dbtemplates.loader import Loader
from dbtemplates.models import Template
from dbtemplates import utils
from cms.models import Page

from .settings import TEMPLATE_CACHE_TIMEOUT

def site_pks_using_template(name):
    pages = Page.objects.filter(template=name)
    sites = pages.values_list('site', flat=True).order_by().distinct()
    return sites


def do_set_site_caches(template_name, content, sites):
    data = {
        utils.cache.get_cache_key(template_name, site): content
        for site in sites
    }
    cache.set_many(data, TEMPLATE_CACHE_TIMEOUT)


def do_invalidate_keys(template, sites):
    def make_key(site):
        return utils.cache.get_cache_key(template, site)
    keys = map(make_key, sites)
    cache.delete_many(keys)


def do_on_template_save(instance, **kwargs):
    name = instance.name
    code = instance.content
    sites = site_pks_using_template(name)
    do_set_site_caches(name, code, sites)


def do_on_template_delete(instance, **kwargs):
    name = instance.name
    sites = site_pks_using_template(name)
    do_invalidate_keys(name, sites)


class CmsTemplatesLoader(Loader):

    def load_and_store_template(self, template_name, cache_key, site, **params):
        """
        Augments the dbtemplates loader by caching templates for other
        sites that are using a given template.
        """
        params.pop('sites__in', None)
        load = super(CmsTemplatesLoader, self).load_and_store_template

        content, display_name = load(template_name, cache_key, site, **params)
        
        # The others sites that use the same template should be set as well.

        sites = site_pks_using_template(template_name)
        do_set_site_caches(template_name, content, sites)
        
        return content, display_name


signals.post_save.connect(do_on_template_save, sender=Template)
signals.pre_delete.connect(do_on_template_delete, sender=Template)
