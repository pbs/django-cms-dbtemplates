from django.conf import settings
from django.core.urlresolvers import resolve
from django.db.models import Q
from djangotoolbox.utils import make_tls_property
from djangotoolbox.sites.dynamicsite import DynamicSiteIDMiddleware
from django.contrib.sites.models import Site
from django.utils.cache import patch_vary_headers

from dbtemplates.models import Template
from cms.models import Page
from cms.utils.permissions import get_user_sites_queryset
from settings import shared_sites, include_orphan
from restricted_admin_decorators import get_restricted_instances

CMS_TEMPLATES = settings.__class__.CMS_TEMPLATES = make_tls_property()


class SiteIDPatchMiddleware(object):
    """ This middleware works together with DynamicSiteIDMiddleware
    from djangotoolbox and patches the site_id based on the
    django-cms cms_admin_site session variable if in admin or
    based on the domain by falling back on DynamicSiteIDMiddleware.
    """
    fallback = DynamicSiteIDMiddleware()

    def process_request(self, request):
        # Use cms_admin_site session variable to guess on what site
        # the user is trying to edit stuff.
        session_site_id = request.session.get('cms_admin_site', None)
        match = resolve(request.path)
        user = getattr(request, 'user', None)

        if (match.app_name == 'admin'
        and match.url_name == 'index'
        and session_site_id is None
        and user is not None
        and not user.is_superuser
        and not user.is_anonymous()):
            sites = get_user_sites_queryset(request.user)
            try:
                s_id = sites[0].pk
                session_site_id = request.session['cms_admin_site'] = s_id
            except IndexError:
                # This user doesn't have any sites under his control.
                pass

        if match.app_name == 'admin' and session_site_id is not None:
            settings.__class__.SITE_ID.value = session_site_id

        else:
            self.fallback.process_request(request)

    def process_response(self, request, response):
        """
        This method patches the 'Vary' response header to include
        'Host' header as a key to cache responses.
        Used by django.middleware.cache
        """
        patch_vary_headers(response, ('Host',))
        return response


class DBTemplatesMiddleware(object):
    def process_request(self, request):

        site_id = request.session.get('cms_admin_site', settings.SITE_ID)
        t = get_restricted_instances(Template, site_id, shared_sites)
        CMS_TEMPLATES.value = [(templ.name, templ.name) for templ in t]
        if not CMS_TEMPLATES.value:
            CMS_TEMPLATES.value = [('dummy',
                                    'Please create a template first.')]

        # This is a huge hack.
        # Expand the model choices field to contain all templates.
        all_templates = Template.objects.all().values_list('name')
        choices = [t * 2 for t in all_templates]
        if settings.CMS_TEMPLATE_INHERITANCE:
            choices += [('INHERIT', 'INHERIT')]
        Page._meta.get_field_by_name('template')[0].choices[:] = choices
