from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.contrib.sites.models import Site
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.core.exceptions import ValidationError
from django.db.models import Q
from settings import shared_sites, include_orphan, restrict_user
from django.conf import settings
from django.forms import ModelMultipleChoiceField

from dbtemplates.models import Template
from dbtemplates.utils.cache import invalidate_cache_for_sites

from cms.models import Page

from restricted_admin_decorators import restricted_has_delete_permission, restricted_get_readonly_fields, restricted_formfield_for_manytomany, restricted_queryset

def _get_registered_modeladmin(model):
    """ This is a huge hack to get the registered modeladmin for the model.
        We need this functionality in case someone else already registered
        a different modeladmin for this model. """
    return type(admin.site._registry[model])

            
allways = ('creation_date', 'last_changed')
ro = ('name', 'content', 'sites') + allways

@restricted_has_delete_permission(restrict_user, tuple(shared_sites))
@restricted_get_readonly_fields(restrict_user, tuple(shared_sites), ro=ro, allways=allways)
@restricted_formfield_for_manytomany(restrict_user)
@restricted_queryset(restrict_user, tuple(shared_sites), include_orphan)
class RestrictedTemplateAdmin(_get_registered_modeladmin(Template)):
    list_filter = ('sites__name', )
    change_form_template = 'cms_templates/change_form.html'

    def change_view(self, request, object_id, extra_context=None):
        extra_context = {'read_only': True} if self._should_hide_save_buttons(request, object_id) else {}
        return super(RestrictedTemplateAdmin, self).change_view(request,
                    object_id, extra_context=extra_context)

    def _should_hide_save_buttons(self, request, object_id):
        if not request.user.is_superuser:
            if restrict_user and shared_sites:
                t = Template.objects.get(pk=object_id)
                if t.sites.filter(name__in=shared_sites):
                    return True
        return False
        
        
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



RegisteredSiteAdmin = _get_registered_modeladmin(Site)
SiteAdminForm = RegisteredSiteAdmin.form


class ExtendedSiteAdminForm(SiteAdminForm):
    templates = ModelMultipleChoiceField(
        queryset=Template.objects.all(),
        required=False,
        widget=FilteredSelectMultiple(
            verbose_name='Templates',
            is_stacked=False
        )
    )

    def __init__(self, *args, **kwargs):
        super(ExtendedSiteAdminForm, self).__init__(*args, **kwargs)
        if self.instance.pk is not None:
            self.fields['templates'].initial = self.instance.template_set.all()

    def clean_templates(self):
        assigned_templates = self.cleaned_data['templates']
        if self.instance.pk is None:
            return assigned_templates
        pks = [s.pk for s in assigned_templates]
        # templates that were previously assigned to this site, but got unassigned
        unassigned_templates = self.instance.template_set.exclude(pk__in=pks)
        templates_with_no_sites = []
        for template in unassigned_templates:
            if template.sites.count() == 1:
                templates_with_no_sites.append(template)
        if templates_with_no_sites:
            raise ValidationError(
                "Following templates will remain with no sites assigned: %s" %
                ", ".join(t.name for t in templates_with_no_sites))
        return assigned_templates

    def save(self, commit=True):
        instance =  super(ExtendedSiteAdminForm, self).save(commit=False)
        # If the object is new, we need to force save it, whether commit
        # is True or False, otherwise setting the template_set would fail
        # This would cause the object to be saved twice if used in an
        # InlineFormSet
        force_save = self.instance.pk is None
        if force_save:
            instance.save()
        instance.template_set = self.cleaned_data['templates']
        if commit:
            if not force_save:
                instance.save()
            self.save_m2m()
        return instance


class ExtendedSiteAdmin(RegisteredSiteAdmin):
    form = ExtendedSiteAdminForm


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
admin.site.register(Site, ExtendedSiteAdmin)
