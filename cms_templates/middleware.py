from django.conf import settings
from django.core.urlresolvers import resolve
from djangotoolbox.utils import make_tls_property
from djangotoolbox.sites.dynamicsite import DynamicSiteIDMiddleware
from django.contrib.sites.models import Site
from django.db.models import Q

from dbtemplates.models import Template
from cms.models import Page


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
            f = (
                Q(globalpagepermission__user=user)
                | Q(globalpagepermission__group__user=user)
            )
            try:
                s_id = Site.objects.filter(f)[0].pk
                settings.__class__.SITE_ID.value = s_id
                request.session['cms_admin_site'] = s_id
            except IndexError:
                pass
        elif match.app_name == 'admin' and session_site_id is not None:
            settings.__class__.SITE_ID.value = session_site_id
        else:
            self.fallback.process_request(request)


class DBTemplatesMiddleware(object):
    def process_request(self, request):
        site_id = request.session.get('cms_admin_site', None)
        available_sites = []
        if site_id:
            available_sites.append(Site.objects.get(pk=site_id))
        try:
            s = Site.objects.get(name='PBS')
        except Site.DoesNotExist:
            pass
        else:
            available_sites.append(s)
        t = Template.objects.filter(sites__in=available_sites).distinct()
        CMS_TEMPLATES.value = [(templ.name, templ.name) for templ in t]
        if not CMS_TEMPLATES.value:
            CMS_TEMPLATES.value = [('dummy', 'Please create a template first.')]

        # This is a huge hack.
        # Expand the model choices field to contain all templates.
        all_templates = Template.objects.all().values_list('name')
        choices = [t*2 for t in all_templates]
        if settings.CMS_TEMPLATE_INHERITANCE:
            choices += [('INHERIT', 'INHERIT')]
        Page._meta.get_field_by_name('template')[0].choices[:] = choices
