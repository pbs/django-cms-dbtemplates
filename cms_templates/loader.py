from dbtemplates.loader import Loader


class CmsTemplatesLoader(Loader):

    def load_and_store_template(self, template_name, cache_key, site, **params):
        params.pop('sites__in', None)
        return super(CmsTemplatesLoader, self).load_and_store_template(
                template_name, cache_key, site, **params)
