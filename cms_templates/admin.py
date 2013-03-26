from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.contrib.sites.models import Site
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.core.exceptions import ValidationError
from settings import shared_sites, include_orphan, restrict_user
from django.conf import settings
from django.forms import ModelMultipleChoiceField
from dbtemplates.models import Template
from cms.models import Page
from django.template import (Template as _Template, TemplateSyntaxError)
from restricted_admin_decorators import restricted_has_delete_permission, \
    restricted_get_readonly_fields, restricted_formfield_for_manytomany, \
    restricted_queryset, restricted_change_view
from django.template.base import TemplateDoesNotExist
from template_analyzer import get_all_templates_used


def _get_registered_modeladmin(model):
    """ This is a huge hack to get the registered modeladmin for the model.
        We need this functionality in case someone else already registered
        a different modeladmin for this model. """
    return type(admin.site._registry[model])

RegisteredTemplateAdmin = _get_registered_modeladmin(Template)
TemplateAdminForm = RegisteredTemplateAdmin.form


def _is_used_by_pages(template, site):
    templates_used = site.page_set.exclude(template='INHERIT')\
        .values_list('template', flat=True)
    if template.name in templates_used:
        return True
    # check if selected template is inherited/used by one of the templates_used
    return False


class ExtendedTemplateAdminForm(TemplateAdminForm):

    def __init__(self, *args, **kwargs):
        super(ExtendedTemplateAdminForm, self).__init__(*args, **kwargs)
        if getattr(self, 'instance', None) and self.instance.pk:
            self.fields['name'].widget.attrs['readonly'] = True

    def _handle_sites_not_assigned(self, template, required_sites):
        already_assigned = template.sites.values_list('domain', flat=True)
        need_assigning = set(required_sites) - set(already_assigned)
        if need_assigning:
            raise ValidationError('The following sites have to be \
                assigned to the template \
                %s: %s' % (template.name, ', '.join(need_assigning)))

    def clean_sites(self):
        if self.instance.pk:
            assigned_sites = self.cleaned_data['sites']\
                .values_list('id', flat=True)
            unassigned_sites = self.instance.sites\
                .exclude(id__in=assigned_sites)
            for site in unassigned_sites:
                if _is_used_by_pages(self.instance, site):
                    raise ValidationError(
                        'Site %s has pages that use this template. \
                        Use different template for pages before \
                        unassigning the site.' % site.domain)
        return self.cleaned_data['sites']

    def clean(self):
        cleaned_data = super(ExtendedTemplateAdminForm, self).clean()
        if not set(['name', 'content', 'sites']) <= set(cleaned_data.keys()):
            return cleaned_data

        required_sites = [site.domain for site in cleaned_data['sites']]

        try:
            compiled_template = _Template(cleaned_data.get('content'))
            used_templates = get_all_templates_used(compiled_template.nodelist)
            print used_templates
        except TemplateSyntaxError, e:
            raise ValidationError('Template Syntax Error: %s' % e)
        except TemplateDoesNotExist, e:

            existing_template = Template.objects.filter(name=str(e))
            if existing_template:
                self._handle_sites_not_assigned(
                    existing_template[0], required_sites)
                raise ValidationError('Template: %s not found.' % e)

            raise ValidationError('Template: %s does not exist. \
                    Create it first and assign it to the following sites: \
                    %s' % (e, ', '.join(required_sites)))

        # make sure all used templates have all necessary sites assigned
        for used_template in set(used_templates):
            self._handle_sites_not_assigned(
                Template.objects.get(name=used_template), required_sites)

        return cleaned_data


allways = ('creation_date', 'last_changed')
ro = ('name', 'content', 'sites') + allways


@restricted_has_delete_permission(restrict_user, tuple(shared_sites))
@restricted_get_readonly_fields(restrict_user, tuple(shared_sites), ro=ro, allways=allways)
@restricted_formfield_for_manytomany(restrict_user)
@restricted_queryset(restrict_user, tuple(shared_sites), include_orphan)
@restricted_change_view(restrict_user, tuple(shared_sites))  # hides all save buttons
class RestrictedTemplateAdmin(RegisteredTemplateAdmin):
    list_filter = ('sites__name', )
    change_form_template = 'cms_templates/change_form.html'
    form = ExtendedTemplateAdminForm


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
        instance = super(ExtendedSiteAdminForm, self).save(commit=False)
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
