from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.contrib.sites.models import Site
from django.db.models import Q
from django.conf import settings

from dbtemplates.models import Template

from cms.models import Page

def _get_registered_modeladmin(model):
    """ This is a huge hack to get the registered modeladmin for the model.
        We need this functionality in case someone else already registered
        a different modeladmin for this model. """
    return type(admin.site._registry[model])


class RestrictedTemplateAdmin(_get_registered_modeladmin(Template)):

    list_filter = ('sites__name', )
    change_form_template = 'cms_templates/change_form.html'


    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "sites":
            kwargs["queryset"] = self._available_sites(request.user)
        return super(RestrictedTemplateAdmin, self).formfield_for_manytomany(
                db_field, request, **kwargs)

    def _available_sites(self, user):
        q = Site.objects.all()
        if not user.is_superuser:
            q = Site.objects.filter(
                Q(globalpagepermission__user=user) |
                Q(globalpagepermission__group__user=user)
            ).distinct()
        return q

    def queryset(self, request):
        q = super(RestrictedTemplateAdmin, self).queryset(request)
        return q.filter(
            Q(sites__in=self._available_sites(request.user)) |
            Q(sites__name='PBS')
        ).distinct()

    def get_readonly_fields(self, request, obj=None):
        allways = ['creation_date', 'last_changed']
        ro = ['name', 'content', 'sites'] + allways
        if not obj or request.user.is_superuser:
            return allways
        s = Site.objects.get(name='PBS')
        if s in obj.sites.all():
            return ro
        return allways

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return False

    def change_view(self, request, object_id, extra_context=None):
        extra_context = {}
        if not request.user.is_superuser:
            t = Template.objects.get(pk=object_id)
            s = Site.objects.get(name='PBS')
            if s in t.sites.all():
                extra_context = {'read_only': True}
        return super(RestrictedTemplateAdmin, self).change_view(request,
                object_id, extra_context=extra_context)


class DynamicTemplatesPageAdmin(_get_registered_modeladmin(Page)):
    def get_form(self, request, obj=None, **kwargs):
        f = super(DynamicTemplatesPageAdmin, self).get_form(
                request, obj, **kwargs)
        choices = settings.CMS_TEMPLATES
        if settings.CMS_TEMPLATE_INHERITANCE:
            choices += [(settings.CMS_TEMPLATE_INHERITANCE_MAGIC,
                       'Inherit the template of the nearest ancestor')]
        f.base_fields['template'].choices = choices
        return f


class TemplateAdminInline(admin.TabularInline):
    model = Template.sites.through
    extra = 1

    def __init__(self, *args, **kwargs):
        super(TemplateAdminInline, self).__init__(*args, **kwargs)


RegisteredSiteAdmin = _get_registered_modeladmin(Site)
RegisteredSiteAdmin.inlines += [TemplateAdminInline]


try:
    admin.site.unregister(Template)
except NotRegistered:
    pass
admin.site.register(Template, RestrictedTemplateAdmin)

try:
    admin.site.unregister(Page)
except NotRegistered:
    pass
admin.site.register(Page, DynamicTemplatesPageAdmin)

try:
    admin.site.unregister(Site)
except NotRegistered:
    pass
admin.site.register(Site, RegisteredSiteAdmin)
