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
from django.db.models import Q


def _get_registered_modeladmin(model):
    """ This is a huge hack to get the registered modeladmin for the model.
        We need this functionality in case someone else already registered
        a different modeladmin for this model. """
    return type(admin.site._registry[model])

RegisteredTemplateAdmin = _get_registered_modeladmin(Template)
TemplateAdminForm = RegisteredTemplateAdmin.form


class ExtendedTemplateAdminForm(TemplateAdminForm):

    custom_error_messages = {
        'template_direct_use': 'Site {0} has pages that are currently using \
            this template. Delete these pages or use different template for \
            them before unassigning the site.',
        'template_indirect_pages_use': 'Site {0} has pages with templates \
            that depend on this template. Delete these pages or use different \
            template for them before unassigning the site.',
        'template_indirect_templ_use': "Cannot unassign site {0} from \
            template {1}. Template {1} is used by template {2} which has \
            site {0} assigned. Both templates need to be unassigned from \
            this site. Do this change from the site admin view.",
        'template_nonexistent_in_page': 'Template {0} is used by pages of the \
            site {1} and does not exist. In order to unassign this site you \
            must fix this error. Create this nonexistent template, delete the \
            pages that uses it or just change the templates from pages with \
            templates that are available for use.',
        'template_syntax_error': 'Syntax error in template {0} or in the \
            templates that depend on it: {1}. Fix this syntax error before \
            unassigning site: {2}.',
        'orphan_in_page': 'Template {0} is used by the site {1}. \
            Template {0} or some of the templates that depend on it do not \
            have site {1} assigned. Assign the site or change the template \
            from the pages that uses it. Fix this error before unassigning \
            site: {1}.',
        'orphan_unassigned_to_site': 'Template {0} is used by the site {1}. \
            Template {0} or some of the templates that are used by it do not \
            have site {1} assigned. Assign the site to fix this error.',
        'missing_template_use': 'Template {0} depends on template {1}. \
            Template {1} does not exist. Create it or remove its reference \
            from the template code.',
    }

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

    def _get_used_templates(self, template_name, site_name, pages_search):
        try:
            template = Template.objects.get(name=template_name)
            return set(get_all_templates_used(_Template(
                template.content).nodelist))
        except Template.DoesNotExist:
            raise ValidationError(
                self.custom_error_messages['template_nonexistent_in_page']
                .format(template_name, site_name)) if pages_search else ''
        except TemplateSyntaxError, e:
            raise ValidationError(
                self.custom_error_messages['template_syntax_error']
                .format(template_name, e, site_name))
        except TemplateDoesNotExist, e:
            try:
                # for orphan templates
                templ_with_missing_site = Template.objects.get(name=str(e))
                raise ValidationError(
                    (self.custom_error_messages['orphan_in_page'] if pages_search
                    else self.custom_error_messages['orphan_unassigned_to_site'])
                    .format(templ_with_missing_site.name, site_name))
            except Template.DoesNotExist:
                raise ValidationError(
                    self.custom_error_messages['missing_template_use']
                    .format(template_name, e))

    def _validate_unassigned_sites(self, cleaned_data):
        assigned = cleaned_data['sites'].values_list('id', flat=True)

        templ_from_unassigned = self.instance.sites\
            .exclude(Q(id__in=assigned) | Q(page__template='INHERIT'))\
            .values_list('page__template', 'domain').distinct()

        if not templ_from_unassigned:
            return

        unassigned_page_templates = {}
        for pair in templ_from_unassigned:
            template_name, domain = pair[0], pair[1]
            unassigned_page_templates.update({
                domain: unassigned_page_templates.get(
                    domain, []) + [template_name]})

        for domain, templates in unassigned_page_templates.iteritems():
            # check if it used by pages
            if self.instance.name in templates:
                raise ValidationError(
                    self.custom_error_messages['template_direct_use']
                    .format(domain))

            # check if it is used by templates of pages
            for template_name in templates:
                if self.instance.name in self._get_used_templates(
                    template_name, domain, True):
                    raise ValidationError(
                        self.custom_error_messages['template_indirect_pages_use']
                        .format(domain))

            # check if it is used by templates of the unassigned site
            assigned_templates = Site.objects.get(domain=domain)\
                .template_set.exclude(name__in=templates)\
                .values_list('name', flat=True)
            for template_name in assigned_templates:
                if self.instance.name in self._get_used_templates(
                    template_name, domain, False):
                    raise ValidationError(
                        self.custom_error_messages['template_indirect_templ_use']
                        .format(domain, self.instance.name, template_name))

    def clean(self):
        cleaned_data = super(ExtendedTemplateAdminForm, self).clean()
        if not set(['name', 'content', 'sites']) <= set(cleaned_data.keys()):
            return cleaned_data

        required_sites = [site.domain for site in cleaned_data['sites']]

        try:
            compiled_template = _Template(cleaned_data.get('content'))
            used_templates = get_all_templates_used(compiled_template.nodelist)
        except TemplateSyntaxError, e:
            raise ValidationError('Template Syntax Error: %s' % e)
        except TemplateDoesNotExist, e:
            try:
                existing_template = Template.objects.get(name=str(e))
                self._handle_sites_not_assigned(
                    existing_template, required_sites)
                raise ValidationError('Template: %s not found.' % e)
            except Template.DoesNotExist:
                raise ValidationError('Template: %s does not exist. \
                        Create it first and assign it to the following sites: \
                        %s' % (e, ', '.join(required_sites)))

        # make sure all used templates have all necessary sites assigned
        for used_template in set(used_templates):
            self._handle_sites_not_assigned(
                Template.objects.get(name=used_template), required_sites)

        if self.instance.pk:
            self._validate_unassigned_sites(cleaned_data)
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
