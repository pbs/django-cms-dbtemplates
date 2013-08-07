from django.contrib.sites.models import Site
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.conf import settings
from django.db.models import Q, Count
from django.forms import ModelMultipleChoiceField
from django.template import (Template as _Template, TemplateSyntaxError)
from django.template.base import TemplateDoesNotExist
from django.db.models import Q, Count, fields
from template_analyzer import get_all_templates_used
from cms.models import Page
from dbtemplates.models import Template
from recursive_validator import handle_recursive_calls, \
    InfiniteRecursivityError, format_recursive_msg
from admin_extend.extend import registered_form, registered_modeladmin, \
    extend_registered, add_bidirectional_m2m
from cms.plugin_pool import plugin_pool
from functools import wraps
from collections import defaultdict


def with_template_debug_on(clean_func):

    @wraps(clean_func)
    def wrapper(*args, **kwargs):
        initial_setting = getattr(settings, 'TEMPLATE_DEBUG')
        try:
            setattr(settings, 'TEMPLATE_DEBUG', True)
            return clean_func(*args, **kwargs)
        finally:
            setattr(settings, 'TEMPLATE_DEBUG', initial_setting)

    return wrapper


def _format_pages(page_qs):
    return ', '.join(['%s(%d)' % (page.get_title() or '', page.id)
                      for page in page_qs])


class ExtendedTemplateAdminForm(registered_form(Template)):

    custom_error_messages = {
        'page_use': ('Site {0} has the following pages that are currently using '
            'this template: {1}. Delete these pages or use different template for '
            'them before unassigning the site.'),
        'page_template_use': ('Site {0} has pages with template {1} assigned.'
            ' Template {1} requires this template. Delete the following '
            'pages or use different template for them before unassigning the'
            ' site: {2}.'),
        'plugin_template_use': ('Cannot unassign site {0} from this '
            'template. Following pages have plugins({1}) that are currently '
            'using this template: {2}'),
        'site_template_use': ('Cannot unassign site {0} from '
            'template {1}. Template {1} is used by template {2} which has '
            'site {0} assigned. Both templates need to be unassigned from '
            'this site. Do this change from the site admin view.'),
        'nonexistent_in_pages': ('Template {0} is used by the following '
            'pages of the site {1} and does not exist: {2}. Create this '
            'nonexistent template, delete the pages that uses it or just '
            'change the template from pages with a template that is '
            'available for use.'),
        'syntax_error_unassigning': ('Syntax error in template {0} or in the '
            'templates that depend on it: {1}. Fix this syntax error before '
            'unassigning site: {2}.'),
        'syntax_error': ('Syntax error in template {0} or in the '
            'templates that depend on it: {1}.'),
        'orphan_in_page': ('Template {0} is used by the site {1}. '
            'Template {0} or some of the templates that depend on it do not '
            'have site {1} assigned. Assign the site or change the template '
            'from the pages that uses it. Fix this error before unassigning '
            'site: {1}.'),
        'orphan_unassigned_to_site': ('Template {0} is used by the site {1}. '
            'Template {0} or some of the templates that are used by it do not '
            'have site {1} assigned. Assign the site to fix this error.'),
        'missing_template_use': ('Template {0} depends on template {1}. '
            'Template {1} does not exist. Create it or remove its reference '
            'from the template code.'),
        'not_found': ('Template: {0} not found.'),
        'missing_sites': ('The following sites have to be assigned to '
            'template {0}: {1}'),
        'infinite_recursivity': ('Infinite template recursivity: {0}'),
    }

    def __init__(self, *args, **kwargs):
        super(ExtendedTemplateAdminForm, self).__init__(*args, **kwargs)
        if getattr(self, 'instance', None) and self.instance.pk:
            if 'name' in self.fields:
                self.fields['name'].widget.attrs['readonly'] = True

    def _error_msg(self, msg_key, *args):
        return self.custom_error_messages[msg_key].format(*args)

    def _handle_sites_not_assigned(self, template, required_sites):
        already_assigned = template.sites.values_list('domain', flat=True)
        need_assigning = set(required_sites) - set(already_assigned)
        if need_assigning:
            raise ValidationError(self._error_msg(
                'missing_sites', template.name, ', '.join(need_assigning)))

    def _get_used_templates(self, template_name, site_domain, pages_search):
        try:
            template = Template.objects.get(name=template_name)
            return set(get_all_templates_used(_Template(
                template.content).nodelist))
        except Template.DoesNotExist:
            if pages_search:
                _pages = Page.objects.filter(
                    site__domain=site_domain, template=template_name)
                raise ValidationError(self._error_msg(
                    'nonexistent_in_pages', template_name, site_domain,
                    _format_pages(_pages)))
        except TemplateSyntaxError, e:
            raise ValidationError(self._error_msg(
                'syntax_error_unassigning', template_name, e, site_domain))
        except TemplateDoesNotExist, e:
            try:
                # for orphan templates
                templ_with_missing_site = Template.objects.get(name=str(e))
                raise ValidationError(self._error_msg(
                    'orphan_in_page' if pages_search
                        else 'orphan_unassigned_to_site',
                        templ_with_missing_site.name, site_domain))
            except Template.DoesNotExist:
                raise ValidationError(self._error_msg(
                    'missing_template_use', template_name, e))

    def _build_template_site_dict(self, list_of_tuples):
        new_dict = defaultdict(list)
        for pair in list_of_tuples:
            template, site = pair[0], pair[1]
            new_dict[site].append(template)
        return new_dict


    def _validate_unassigned_sites(self, cleaned_data):
        assigned = cleaned_data['sites'].values_list('id', flat=True)

        unassigned_page_templates = self._build_template_site_dict(
            self.instance.sites.exclude(
                Q(id__in=assigned) | Q(page__template='INHERIT'))
            .values_list('page__template', 'domain').distinct())

        sites_about_to_be_unassigned = self.instance.sites.exclude(id__in=assigned)
        unassigned_site_templates = {
            s.domain: s.template_set.all().values_list('name', flat=True)
            for s in sites_about_to_be_unassigned}

        if not (unassigned_page_templates or unassigned_site_templates):
            return

        current_templ = self.instance.name
        compiled = {}
        for domain, templates in unassigned_page_templates.iteritems():
            # check if it used by pages
            if current_templ in templates:
                _pages = Page.objects.filter(
                    site__domain=domain, template=current_templ)
                raise ValidationError(self._error_msg(
                    'page_use', domain, _format_pages(_pages)))

            # check if it is used by templates of pages
            for template_name in templates:
                _templs_of_template = compiled.setdefault(template_name,
                    self._get_used_templates(template_name, domain, True))

                if current_templ in _templs_of_template:
                    _pages = Page.objects.filter(
                        site__domain=domain, template=template_name)
                    raise ValidationError(self._error_msg(
                        'page_template_use', domain, template_name,
                        _format_pages(_pages)))

        for domain, other_templates in unassigned_site_templates.iteritems():
            # check if it is used by templates of the unassigned site
            for template_name in other_templates:
                _templs_of_template = compiled.setdefault(template_name,
                    self._get_used_templates(template_name, domain, False))

                if current_templ in _templs_of_template:
                    raise ValidationError(self._error_msg(
                        'site_template_use', domain, current_templ, template_name))

        for site in sites_about_to_be_unassigned:
            templ_with_plugins = get_plugin_templates_from_site(site)
            if current_templ in templ_with_plugins:
                _page_ids = get_pages_for_plugins_templates(
                    site, current_templ, templ_with_plugins[current_templ])
                _pages = Page.objects.filter(id__in=_page_ids)
                raise ValidationError(self._error_msg(
                    'plugin_template_use', site.domain,
                    ', '.join(templ_with_plugins[current_templ]),
                    _format_pages(_pages)))

    @with_template_debug_on
    def clean(self):
        cleaned_data = super(ExtendedTemplateAdminForm, self).clean()
        if not set(['name', 'content', 'sites']) <= set(cleaned_data.keys()):
            return cleaned_data

        required_sites = [site.domain for site in cleaned_data['sites']]

        try:
            compiled_template = _Template(cleaned_data.get('content'))

            #here the template syntax is valid
            handle_recursive_calls(cleaned_data['name'], cleaned_data['content'])

            used_templates = get_all_templates_used(compiled_template.nodelist)
        except TemplateSyntaxError, e:
            raise ValidationError(
                self._error_msg('syntax_error', cleaned_data['name'], e))
        except InfiniteRecursivityError, e:
            msg = format_recursive_msg(cleaned_data['name'], e)
            raise ValidationError(
                self._error_msg('infinite_recursivity', msg))
        except TemplateDoesNotExist, e:
            try:
                existing_template = Template.objects.get(name=str(e))
                self._handle_sites_not_assigned(
                    existing_template, required_sites)
                raise ValidationError(self._error_msg('not_found', e))
            except Template.DoesNotExist:
                raise ValidationError(self._error_msg(
                        'missing_template_use', cleaned_data['name'], e))

        # make sure all used templates have all necessary sites assigned
        for used_template in set(used_templates):
            try:
                _used_template = Template.objects.get(name=used_template)
            except Template.DoesNotExist, e:
                raise ValidationError(self._error_msg(
                     'missing_template_use', cleaned_data['name'], used_template))
            else:
                self._handle_sites_not_assigned(
                    _used_template, required_sites)

        if self.instance.pk:
            self._validate_unassigned_sites(cleaned_data)

        return cleaned_data


@extend_registered
class RestrictedTemplateAdmin(registered_modeladmin(Template)):
    list_filter = ('sites__name', )
    change_form_template = 'cms_templates/change_form.html'
    form = ExtendedTemplateAdminForm


@extend_registered
class DynamicTemplatesPageAdmin(registered_modeladmin(Page)):
    def get_form(self, request, obj=None, **kwargs):
        f = super(DynamicTemplatesPageAdmin, self).get_form(
            request, obj, **kwargs)
        choices = settings.CMS_TEMPLATES
        f.base_fields['template'].choices = choices
        return f


@extend_registered
class ExtendedSiteAdminForm(add_bidirectional_m2m(registered_form(Site))):
    templates = ModelMultipleChoiceField(
        queryset=Template.objects.all(),
        required=False,
        widget=FilteredSelectMultiple(
            verbose_name='Templates',
            is_stacked=False
        )
    )

    def _get_bidirectional_m2m_fields(self):
        return super(ExtendedSiteAdminForm, self).\
            _get_bidirectional_m2m_fields() + [('templates', 'template_set')]

    custom_error_messages = {
        'syntax_error': ('Template {0} or some of the templates it uses have '
            'syntax errors: {1}. Fix this error before assigning/unassigning '
            'this template.'),
        'required_not_assigned': ('Template {0} is required by template {1} '
            'and it is not assigned to this site.'),
        'required_not_exist': ('Template {0} uses template {1} that does not '
            'exist. Create it or remove its reference from the template code. '
            'Fix this error before assigning/unassigning this template.'),
        'all_required': ('Template(s) {0} are required by template {1}. Assign '
            'or unassign them all.'),
        'nonexistent_in_pages': ('There are pages that use the following '
            'nonexistent templates: {0}. Change/delete the following pages '
            'that uses them or just create them with this site assigned: {1}.'),
        'required_in_pages': ('Templates {0} are used by the following pages '
            'of this site and need to be assigned to this site: {1}'),
        'nonexistent_in_plugins': ('There are pages with plugins that use '
            'the following nonexistent templates: {0}. Change/delete the '
            'plugins that uses them, or just create them with this '
            'site assigned. Check the following pages to fix plugins({1}): {2}'),
        'required_in_plugins': ('Template {0} is used by plugins({1})'
            ' in the following pages of this site and need to be assigned '
            'to this site: {2}'),
        'orphan': ('Following templates will remain with no sites assigned: {0}'),
    }

    def _error_msg(self, msg_key, *args):
        return self.custom_error_messages[msg_key].format(*args)

    def _get_templates_used(self, template_instance):
        try:
            compiled_template = _Template(template_instance.content)
            used_templates = get_all_templates_used(compiled_template.nodelist)
        except TemplateSyntaxError, e:
            raise ValidationError(
                self._error_msg('syntax_error', template_instance.name, e))
        except TemplateDoesNotExist, e:
            try:
                existing_template = Template.objects.get(name=str(e))
                if existing_template not in self.cleaned_data['templates']:
                    raise ValidationError(self._error_msg(
                        'required_not_assigned', e, template_instance.name))
            except Template.DoesNotExist:
                raise ValidationError(self._error_msg(
                    'required_not_exist', template_instance.name, e))
        return used_templates

    @with_template_debug_on
    def clean_templates(self):
        assigned_templates = self.cleaned_data['templates']

        assigned_names = set([t.name for t in assigned_templates])
        for assigned_templ in assigned_templates:
            used = set(self._get_templates_used(assigned_templ))
            if not used <= assigned_names:
                raise ValidationError(self._error_msg(
                    'all_required', ', '.join(used - assigned_names),
                        assigned_templ.name))

        if self.instance.pk is None:
            return assigned_templates

        templates_required = set(self.instance.page_set
            .exclude(template__in=list(assigned_names) + ['INHERIT'])
            .values_list('template', flat=True).distinct())

        templ_with_plugins = get_plugin_templates_from_site(self.instance)
        plugins_templ = set(templ_with_plugins.keys()) - assigned_names

        if templates_required or plugins_templ:
            all_existing_templates = set(Template.objects.all()
                .values_list('name', flat=True))

            nonexistent = templates_required - all_existing_templates
            if nonexistent:
                _pages = self.instance.page_set.filter(
                    template__in=nonexistent)
                raise ValidationError(self._error_msg(
                    'nonexistent_in_pages',
                    ', '.join(nonexistent), _format_pages(_pages)))
            nonexistent = plugins_templ - all_existing_templates
            if nonexistent:
                first_nonexistent = iter(nonexistent).next()
                _page_ids = get_pages_for_plugins_templates(
                    self.instance, first_nonexistent,
                    templ_with_plugins[first_nonexistent])
                _pages = Page.objects.filter(id__in=_page_ids)
                raise ValidationError(self._error_msg(
                    'nonexistent_in_plugins', first_nonexistent,
                    ', '.join(templ_with_plugins[first_nonexistent]),
                    _format_pages(_pages)))

            if templates_required:
                _pages = self.instance.page_set.filter(
                    template__in=templates_required)
                raise ValidationError(self._error_msg(
                    'required_in_pages', ', '.join(templates_required),
                    _format_pages(_pages)))
            if plugins_templ:
                first_required = iter(plugins_templ).next()
                _page_ids = get_pages_for_plugins_templates(
                    self.instance, first_required,
                    templ_with_plugins[first_required])
                _pages = Page.objects.filter(id__in=_page_ids)
                raise ValidationError(self._error_msg(
                    'required_in_plugins', first_required,
                    ', '.join(templ_with_plugins[first_required]),
                    _format_pages(_pages)))

        pks = [s.pk for s in assigned_templates]
        unassigned = self.instance.template_set.exclude(pk__in=pks)\
            .values_list('id', flat=True)

        orphan_templates = Template.objects.filter(id__in=unassigned)\
            .annotate(Count('sites')).filter(sites__count=1)\
            .values_list('name', flat=True)

        if orphan_templates:
            raise ValidationError(
                self._error_msg('orphan', ", ".join(orphan_templates)))

        return assigned_templates


# validate PLUGIN_TEMPLATE_REFERENCES configuration
_VALID_TEMPLATE_FIELDS = [fields.related.ForeignKey, fields.CharField]
for plugin_name in settings.PLUGIN_TEMPLATE_REFERENCES:
    # make sure all plugins are dicovered
    plugin_pool.get_all_plugins()

    if plugin_name not in plugin_pool.plugins:
        raise ImproperlyConfigured(
            'setting PLUGIN_TEMPLATE_REFERENCES improperly configured: '
            'CMS Plugin %s not found' % plugin_name)

    plugin_class = plugin_pool.get_plugin(plugin_name)
    if not hasattr(plugin_class, 'get_template_field_name'):
        raise AttributeError(
            'CMS plugin %s must implement \'get_template_field_name\' '
            'staticmethod.' % plugin_name)

    model_opts = plugin_class.model._meta
    field_name = plugin_class.get_template_field_name()
    if field_name not in model_opts.get_all_field_names():
        raise fields.FieldDoesNotExist(
            'CMS plugin %s must implement \'get_template_field_name\' '
            'class method that returns a valid model template field '
            'name.' % plugin_name)

    field_type = model_opts.get_field_by_name(field_name)[0].__class__
    if field_type not in _VALID_TEMPLATE_FIELDS:
        raise AttributeError(
            'CMS Plugin %s method \'get_template_field_name\' must return '
            'the name of a valid template field. The template field '
            'type must be one of: %s' % (
                plugin_name, ','.join(_VALID_TEMPLATE_FIELDS)))


def _get_template_name_attr(model, field_name):
    field_type = model._meta.get_field_by_name(field_name)[0].__class__
    is_str = field_type is fields.CharField
    return field_name if is_str else '%s__name' % field_name


def _get_plugin_metadata(plugin_name):
    plugin_class = plugin_pool.get_plugin(plugin_name)
    plugin_model = plugin_class.model
    field_name = plugin_class.get_template_field_name()
    template_name_attr = _get_template_name_attr(
        plugin_model, field_name)
    return plugin_model, field_name, template_name_attr


def _get_templates_from_plugin(site, plugin_name):
    plugin_model, field_name, template_name_attr = _get_plugin_metadata(plugin_name)

    return plugin_model.objects.filter(**{
        'placeholder__page__site': site,
        '%s__isnull' % field_name: False
    }).values_list(template_name_attr, flat=True)


def get_plugin_templates_from_site(site):
    templates = defaultdict(set)
    for plugin in settings.PLUGIN_TEMPLATE_REFERENCES:
        for template in _get_templates_from_plugin(site, plugin):
            templates[template].add(plugin)
    return templates


def get_pages_for_plugins_templates(site, template_name, plugins):
    pages = []
    for plugin in plugins:
        plugin_model, field_name, template_name_attr = _get_plugin_metadata(plugin)
        pages += plugin_model.objects.filter(**{
            'placeholder__page__site': site,
            '%s__isnull' % field_name: False,
            template_name_attr: template_name
        }).values_list('placeholder__page', flat=True)
    return pages
