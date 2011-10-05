from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.contrib.sites.models import Site
from django.db.models import Q

from dbtemplates.admin import TemplateAdmin
from dbtemplates.models import Template
from cms.models import GlobalPagePermission


class RestrictedTemplateAdmin(TemplateAdmin):

    list_filter = ('sites__name', )
    change_form_template = 'cms_templates/change_form.html'


    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "sites":
            kwargs["queryset"] = self._available_sites(request.user)
        return super(TemplateAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

    def _available_sites(self, user):
        q = Site.objects.all()
        if not user.is_superuser:
            global_pages = GlobalPagePermission.objects.filter(user=user)
            q = Site.objects.filter(globalpagepermission__in=global_pages)
        return q.distinct()

    def queryset(self, request):
        q = super(TemplateAdmin, self).queryset(request)
        return q.filter(
            Q(sites__in=self._available_sites(request.user)) |
            Q(sites=Site.objects.get(name='PBS'))
        ).distinct()

    def get_readonly_fields(self, request, obj=None):
        ro = ['name', 'content', 'sites', 'creation_date', 'last_changed']
        if not obj or request.user.is_superuser:
            return []
        s = Site.objects.get(name='PBS')
        if s in obj.sites.all():
            return ro
        return []

    def has_delete_permission(self, request, obj=None):
        if not obj or request.user.is_superuser:
            return True
        s = Site.objects.get(name='PBS')
        if s in obj.sites.all():
            return False
        return True

    def change_view(self, request, object_id, extra_context=None):
        extra_context = {}
        if not request.user.is_superuser:
            t = Template.objects.get(pk=object_id)
            s = Site.objects.get(name='PBS')
            if s in t.sites.all():
                extra_context = {'read_only': True}
        return super(RestrictedTemplateAdmin, self).change_view(request,
                object_id, extra_context=extra_context)


try:
    admin.site.unregister(Template)
except NotRegistered:
    pass
admin.site.register(Template, RestrictedTemplateAdmin)
