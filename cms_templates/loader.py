from dbtemplates.loader import Loader
from settings import shared_sites
from django.contrib.sites.models import Site

class CmsTemplatesLoader(Loader):

    def load_and_store_template(self, template_name, cache_key, site, **params):
        if params.has_key('sites__in'):
            site_ids =  params['sites__in'] + [s.id for s in Site.objects.filter(name__in=shared_sites)]
            return super(CmsTemplatesLoader, self).load_and_store_template(
                template_name, cache_key, site, sites__in=site_ids)
        return super(CmsTemplatesLoader, self).load_and_store_template(
                template_name, cache_key, site, **params)
        