from dbtemplates.loader import Loader
from settings import shared_sites
from django.contrib.sites.models import Site

class CmsTemplatesLoader(Loader):

    def load_and_store_template(self, template_name, cache_key, site, **params):
        sites_in = params.get('sites__in', None)
        if sites_in:
            site_ids = [s.id for s in Site.objects.filter(name__in=shared_sites)] + sites_in
            return super(CmsTemplatesLoader, self).load_and_store_template(
                template_name, cache_key, site, sites__in=site_ids)
        return super(CmsTemplatesLoader, self).load_and_store_template(
                template_name, cache_key, site, **params)
        