from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from django.contrib.sites.models import Site
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.core.exceptions import ValidationError
from django.conf import settings
from django.forms import ModelMultipleChoiceField
from dbtemplates.models import Template
from cms.models import Page
from django.template import (Template as _Template, TemplateSyntaxError)
from django.template.base import TemplateDoesNotExist
from template_analyzer import get_all_templates_used
from django.db.models import Q, Count
from recursive_validator import handle_recursive_calls, \
    InfiniteRecursivityError, format_recursive_msg
from cms.plugin_pool import plugin_pool
from cms_templates import settings as cms_tpl_settings

from admin_extend.extend import registered_form, registered_modeladmin, \
    extend_registered, add_bidirectional_m2m


class ExtendedTemplateAdminForm(registered_form(Template)):

    custom_error_messages = {
        'page_use': ('Site {0} has pages that are currently using '
            'this template. Delete these pages or use different template for '
            'them before unassigning the site.'),
        'page_template_use': ('Site {0} has pages with templates '
            'that depend on this template. Delete these pages or use different '
            'template for them before unassigning the site.'),
        'external_plugin_template_use': ('Cannot unassign site {0} from '
            'template {2}. There are pages with {1}(s) using template {2}.'),
        'site_template_use': ('Cannot unassign site {0} from '
            'template {1}. Template {1} is used by template {2} which has '
            'site {0} assigned. Both templates need to be unassigned from '
            'this site. Do this change from the site admin view.'),
        'nonexistent_in_pages': ('Template {0} is used by pages of the '
            'site {1} and does not exist. In order to unassign this site you '
            'must fix this error. Create this nonexistent template, delete the '
            'pages that uses it or just change the templates from pages with '
            'templates that are available for use.'),
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

    def _get_used_templates(self, template_name, site_name, pages_search):
        try:
            template = Template.objects.get(name=template_name)
            return set(get_all_templates_used(_Template(
                template.content).nodelist))
        except Template.DoesNotExist:
            if pages_search:
                raise ValidationError(self._error_msg(
                    'nonexistent_in_pages', template_name, site_name))
        except TemplateSyntaxError, e:
            raise ValidationError(self._error_msg(
                'syntax_error_unassigning', template_name, e, site_name))
        except TemplateDoesNotExist, e:
            try:
                # for orphan templates
                templ_with_missing_site = Template.objects.get(name=str(e))
                raise ValidationError(self._error_msg(
                    'orphan_in_page' if pages_search
                        else 'orphan_unassigned_to_site',
                        templ_with_missing_site.name, site_name))
            except Template.DoesNotExist:
                raise ValidationError(self._error_msg(
                    'missing_template_use', template_name, e))

    def _build_template_site_dict(self, list_of_tuples):
        new_dict = {}
        for pair in list_of_tuples:
            template, site = pair[0], pair[1]
            new_dict.update({site: new_dict.get(site, []) + [template]})
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

        compiled = {}
        for domain, templates in unassigned_page_templates.iteritems():
            # check if it used by pages
            if self.instance.name in templates:
                raise ValidationError(self._error_msg('page_use', domain))

            # check if it is used by templates of pages
            for template_name in templates:

                if template_name not in compiled:
                    compiled[template_name] = self._get_used_templates(
                        template_name, domain, True)

                if self.instance.name in compiled.get(template_name):
                    raise ValidationError(self._error_msg(
                        'page_template_use', domain))

        for domain, other_templates in unassigned_site_templates.iteritems():
            # check if it is used by templates of the unassigned site

            for template_name in other_templates:

                if template_name not in compiled:
                    compiled[template_name] = self._get_used_templates(
                        template_name, domain, False)

                if self.instance.name in compiled.get(template_name):
                    raise ValidationError(self._error_msg(
                        'site_template_use', domain, self.instance.name, template_name))

        for site in sites_about_to_be_unassigned:
            # check if it is used by other cms plugins
            for plugin in cms_tpl_settings.PLUGIN_TEMPLATE_REFERENCES:
                if self.instance.name in _get_plugin_templates(site, plugin):
                    plugin_cls = plugin_pool.get_plugin(plugin)
                    raise ValidationError(self._error_msg(
                        'external_plugin_template_use', \
                        site.name, plugin_cls.name, self.instance))

    def clean(self):
        cleaned_data = super(ExtendedTemplateAdminForm, self).clean()
        if not set(['name', 'content', 'sites']) <= set(cleaned_data.keys()):
            return cleaned_data

        initial_setting = getattr(settings, 'TEMPLATE_DEBUG')

        try:
            setattr(settings, 'TEMPLATE_DEBUG', True)

            try:
                handle_recursive_calls(cleaned_data['name'], cleaned_data['content'])
            except InfiniteRecursivityError, e:
                msg = format_recursive_msg(cleaned_data['name'], e)
                raise ValidationError(
                    self._error_msg('infinite_recursivity', msg))

            required_sites = [site.domain for site in cleaned_data['sites']]

            try:
                compiled_template = _Template(cleaned_data.get('content'))
                used_templates = get_all_templates_used(compiled_template.nodelist)
            except TemplateSyntaxError, e:
                raise ValidationError(
                    self._error_msg('syntax_error', cleaned_data['name'], e))
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

            setattr(settings, 'TEMPLATE_DEBUG', initial_setting)
            return cleaned_data
        except:
            setattr(settings, 'TEMPLATE_DEBUG', initial_setting)
            raise


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
    template = ModelMultipleChoiceField(
        queryset=Template.objects.all(),
        required=False,
        widget=FilteredSelectMultiple(
            verbose_name='Templates',
            is_stacked=False
        )
    )

    def _get_bidirectinal_m2m_fields(self):
        return super(ExtendedSiteAdminForm, self).\
            _get_bidirectinal_m2m_fields() + ['template']

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
            'nonexistent templates: {0}. Change the pages that uses them, '
            'delete the pages that uses them or just create them with this '
            'site assigned.'),
        'required_in_pages': ('The following templates are used by the pages '
            'of this site and need to be assigned to this site: {0}'),
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

    def clean_templates(self):
        assigned_templates = self.cleaned_data['templates']

        initial_setting = getattr(settings, 'TEMPLATE_DEBUG')
        try:
            setattr(settings, 'TEMPLATE_DEBUG', True)
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
            external_plugis_tpls = _get_external_plugins_templates(self.instance)
            templates_required |= external_plugis_tpls - assigned_names

            if templates_required:
                all_existing_templates = set(Template.objects.all()
                    .values_list('name', flat=True))
                if not templates_required <= all_existing_templates:
                    raise ValidationError(self._error_msg(
                        'nonexistent_in_pages',
                        ', '.join(templates_required - all_existing_templates)))
                else:
                    raise ValidationError(self._error_msg(
                        'required_in_pages', ', '.join(templates_required)))

            pks = [s.pk for s in assigned_templates]
            unassigned = self.instance.template_set.exclude(pk__in=pks)\
                .values_list('id', flat=True)

            orphan_templates = Template.objects.filter(id__in=unassigned)\
                .annotate(Count('sites')).filter(sites__count=1)\
                .values_list('name', flat=True)

            if orphan_templates:
                raise ValidationError(
                    self._error_msg('orphan', ", ".join(orphan_templates)))
            setattr(settings, 'TEMPLATE_DEBUG', initial_setting)
            return assigned_templates
        except:
            setattr(settings, 'TEMPLATE_DEBUG', initial_setting)
            raise


def _get_external_plugins_templates(site):
    templates = set([])
    for plugin in cms_tpl_settings.PLUGIN_TEMPLATE_REFERENCES:
        templates |= set(_get_plugin_templates(site, plugin))
    return templates


import logging
logger = logging.getLogger(__package__)


def _get_plugin_templates(site, plg_name):
    try:
        plugin_cls = plugin_pool.get_plugin(plg_name)
        return plugin_cls.get_templates(site)
    except KeyError:
        logger.warning('setting PLUGIN_TEMPLATE_REFERENCES improperly configured: '
                       'cms plugin %s not found.' % plg_name)
    except AttributeError:
        logger.warning('cms plugin %s must implement \'get_templates\' class method.')

    return set([])
