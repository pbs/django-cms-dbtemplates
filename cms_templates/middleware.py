import logging

from django.conf import settings
from django.http import Http404
from django.core.urlresolvers import resolve
from django.db.models import Q
from djangotoolbox.utils import make_tls_property
from djangotoolbox.sites.dynamicsite import DynamicSiteIDMiddleware
from django.contrib.sites.models import Site
from django.utils.cache import patch_vary_headers

from dbtemplates.models import Template
from cms.models import Page
from cms.utils.permissions import get_user_sites_queryset
from settings import include_orphan
from django.core.exceptions import PermissionDenied

logger = logging.getLogger(__name__)

CMS_TEMPLATES = settings.__class__.CMS_TEMPLATES = make_tls_property()
CMS_TEMPLATE_INHERITANCE_TITLE = 'Inherit the template of the nearest ancestor'


class SiteIDPatchMiddleware(object):
    """ This middleware works together with DynamicSiteIDMiddleware
    from djangotoolbox and patches the site id based on the
    django-cms cms_admin_site session variable if in admin or
    based on the domain by falling back on DynamicSiteIDMiddleware.
    """
    fallback = DynamicSiteIDMiddleware()

    def process_request(self, request):
        # Use cms_admin_site session variable to guess on what site
        # the user is trying to edit stuff.
        session_site_id = request.session.get('cms_admin_site', None)
        try:
            match = resolve(request.path)
        except Exception as e:
            logger.warning("SiteIDPatchMiddleware is raising {0}\n\n. "
                           "Using {1} and bubble up".format(e, self.fallback))
            self.fallback.process_request(request)
            raise e
        user = getattr(request, 'user', None)

        if (match.app_name == 'admin'
        and session_site_id is None
        and user is not None
        and not user.is_superuser
        and not user.is_anonymous()):
            self.fallback.process_request(request)
            session_site_id = settings.__class__.SITE_ID.value
            allowed_sites = list(get_user_sites_queryset(request.user)
                .values_list('id', flat=True))
            if allowed_sites:
                # change site only if current site is not allowed
                if session_site_id not in allowed_sites:
                    session_site_id = allowed_sites[0]
                request.session['cms_admin_site'] = session_site_id
            elif match.url_name != "index":
                raise PermissionDenied

        if match.app_name == 'admin' and session_site_id is not None:
            settings.__class__.SITE_ID.value = session_site_id
        else:
            self.fallback.process_request(request)

        if not settings.__class__.SITE_ID.value:
            # This user doesn't have any sites under his control.
            logger.error("SiteIDPatchMiddleware ended and nothing worked! "
                         "And now a Http404 will be raised.")
            raise Http404

    def process_response(self, request, response):
        """
        This method patches the 'Vary' response header to include
        'Host' header as a key to cache responses.
        Used by django.middleware.cache
        """
        patch_vary_headers(response, ('Host',))
        return response


def get_site_templates(site_id=None):
    """Return the list of templates defined for a given site.

       In case no site is specified, the current site is considered.
    """
    if site_id:
        f = Q(sites=Site.objects.get(pk=site_id))
    else:
        f = Q(sites=Site.objects.get_current())
    return Template.objects.filter(f).distinct()


class DBTemplatesMiddleware(object):
    def process_request(self, request):
        site_id = request.session.get('cms_admin_site', settings.SITE_ID)
        try:
            templates = get_site_templates(site_id)
        except Site.DoesNotExist:
            logger.error('Current site not found: %d. '
                         'It was probably deleted' % site_id)
            raise Http404
        CMS_TEMPLATES.value = [(templ.name, templ.name) for templ in templates]
        if not CMS_TEMPLATES.value:
            CMS_TEMPLATES.value = [('dummy',
                                    'Please create a template first.')]

        # This is a huge hack.
        # Expand the model choices field to contain all templates.
        all_templates = Template.objects.all().values_list('name')
        choices = [templates * 2 for templates in all_templates]
        if settings.CMS_TEMPLATE_INHERITANCE:
            choices += [(settings.CMS_TEMPLATE_INHERITANCE_MAGIC,
                         CMS_TEMPLATE_INHERITANCE_TITLE)]
        Page._meta.get_field_by_name('template')[0].choices[:] = choices
        CMS_TEMPLATES.value.append((settings.CMS_TEMPLATE_INHERITANCE_MAGIC,
                                    CMS_TEMPLATE_INHERITANCE_TITLE))
