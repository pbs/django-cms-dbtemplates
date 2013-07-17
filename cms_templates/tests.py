from django.test import TestCase
from dbtemplates.models import Template
from django.contrib.sites.models import Site
from django.contrib.auth.models import User, Group
from django.contrib.admin.options import ModelAdmin
from django.test.client import RequestFactory
from django.template import loader, Context, TemplateDoesNotExist
from django.core import urlresolvers
from django.conf import settings
from cms.models.permissionmodels import GlobalPagePermission
from cms.models import Page, Title
from urlparse import urljoin
from cms.test_utils.testcases import (CMSTestCase,
                                      URL_CMS_PAGE,
                                      URL_CMS_PAGE_ADD,)

from mock import patch
import re
from recursive_validator import handle_recursive_calls, \
    InfiniteRecursivityError


def _fix_lang_url(url):
    """
    We don't use the multilingual url middleware from django cms and because
    in their test_utils each URL_* variable is prefixed with '/en' we need to
    remove that.
    """
    middleware = 'cms.middleware.multilingual.MultilingualURLMiddleware'
    no_multilang_url = middleware not in settings.MIDDLEWARE_CLASSES
    if no_multilang_url:
        lang_prefix = '/' + settings.CMS_LANGUAGES[0][0]
        lang_length = len(lang_prefix)
        url_fixer = lambda url: url[lang_length:]
    else:
        url_fixer = lambda url: url
    return url_fixer(url)

URL_CMS_PAGE = _fix_lang_url(URL_CMS_PAGE)
URL_CMS_PAGE_ADD = _fix_lang_url(URL_CMS_PAGE_ADD)


class TestLoader(TestCase):

    def test_shared_site_template(self):
        with patch('cms_templates.settings.shared_sites') as mock:
            mock.return_value = ['SHARED_SITE']
            shared_site = Site.objects.create(domain="shared_site.org",
                                              name="SHARED_SITE")
            site1 = Site.objects.create(domain="site1.org", name="site1")
            settings.__class__.SITE_ID.value = site1.id
            site2 = Site.objects.create(domain="site2.org", name="site2")
            t1_shared = Template.objects.create(name='shared.html',
                                                content='shared')
            t1_shared.sites.clear()
            t1_shared.sites.add(shared_site)
            t1_s1 = Template.objects.create(name='site1.html',
                                            content='site1')
            t1_s1.sites.clear()
            t1_s1.sites.add(site1)
            t2_s2 = Template.objects.create(name='site2.html',
                                            content='site2')
            t2_s2.sites.clear()
            t2_s2.sites.add(site2)
            tpl = loader.get_template('site1.html')
            self.assertEqual(tpl.render(Context({})), 'site1')
                # test that template assigned to the shared site (SHARED_SITE)
                # is available for site1
            tpl = loader.get_template('shared.html')
            self.assertEqual(tpl.render(Context({})), 'shared')


    def test_shared_template_assigned_also_to_another_site(self):
        #test that no exception is raised because the shared template belongs
        #to both shared site and site1
        with patch('cms_templates.settings.shared_sites') as mock:
            mock.return_value = ['SHARED_SITE']
            shared_site = Site.objects.create(domain="shared_site.org",
                                              name="SHARED_SITE")
            site1 = Site.objects.create(domain="site1.org", name="site1")
            settings.__class__.SITE_ID.value = site1.id
            t1_shared = Template.objects.create(name='shared.html',
                                                content='shared')
            #shared template belongs to both sites
            t1_shared.sites.clear()
            t1_shared.sites.add(shared_site, site1)
            t1_s1 = Template.objects.create(name='site1.html',
                                            content='site1')
            t1_s1.sites.clear()
            t1_s1.sites.add(site1)
            tpl = loader.get_template('shared.html')
            self.assertEqual(tpl.render(Context({})), 'shared')

    def test_orphan(self):
        #test that the orphan site can be loaded
        site1 = Site.objects.create(domain="site1.org", name="site1")
        settings.__class__.SITE_ID.value = site1.id
        t_orphan = Template.objects.create(name='orphan.html',
                                           content='orphan')
        template = loader.get_template('orphan.html')
        self.assertEqual(template.render(Context({})), 'orphan')


class AdminParentChildInheritTest(CMSTestCase):
    """
    Creates two pages, Parent and Child both with the same template assigned.
    Changes the Child's template to inherit.
    """
    template_content = """
        {% load cms_tags sekizai_tags %}
        <!doctype html>
        <head>
          <title>{{ request.current_page.get_title }}</title>
          {% render_block "css" %}
        </head>
        <body>
        {% cms_toolbar %}
            {% placeholder "main" %}
            <!--second_placeholder-->
        {% render_block "js" %}
        </body>
        </html>
        """

    def setUp(self):
        """Creates the test site, and the two templates"""
        username = 'page_template_test'
        try:
            User.objects.get(username__exact=username)
        except User.DoesNotExist:
            User.objects.create_superuser(
                username=username, password='x',
                email='%s@templates.com' % username)
        self.client.login(username=username, password='x')
        session = self.client.session
        session['cms_admin_site'] = 1
        session.save()
        self.site = Site.objects.get(id=1)
        self.client.get('/admin/')
        first_data = self.template_content
        second_data = self.template_content.replace(
            '<!--second_placeholder-->',
            '{% placeholder "content" %}',
        )
        first_template, _ = Template.objects.get_or_create(
            name='first.html',
            content=first_data,
        )
        second_template, _ = Template.objects.get_or_create(
            name='second.html',
            content=second_data,
        )
        first_template.sites.add(self.site)
        second_template.sites.add(self.site)

    def test_set_template_to_inherit(self):
        """
        Creates Parent and Child pages.
        Sets the child's template to inherit.
        """
        pass
        parent_id = self._create_page(
            'first.html', 'parent', 'parent'
        )
        child_id = self._create_page(
            'second.html', 'child', 'child', parent_id
        )

        page_data = self.get_new_page_data()
        page_data.update({
            'template': settings.CMS_TEMPLATE_INHERITANCE_MAGIC,
            'site': self.site.pk,
            'slug': 'child',
            'title': 'child',
            'parent': parent_id,
        })
        url_format = urljoin(URL_CMS_PAGE, '{page_id}/')
        page_url = url_format.format(page_id=child_id)
        response = self.client.post(page_url, page_data)
        self.assertRedirects(response, URL_CMS_PAGE)
        page = Page.objects.get(pk=child_id)
        self.assertEqual(page.template,
                         settings.CMS_TEMPLATE_INHERITANCE_MAGIC)

    def test_create_page(self):
        """Test that a page can be created via the admin"""
        self._create_page(
            template='second.html',
            slug='my_slug',
            title='my_title',
        )

    def test_templates_created(self):
        """Tests that two templates are created, first and second"""
        self.assertEqual(2, len(Template.objects.all()))
        self.assertIsNot(Template.objects.get(name='first.html'), [])
        self.assertIsNot(Template.objects.get(name='second.html'), [])

    def _create_page(self, template, slug, title, parent_id=None):
        """
        Creates a page with the template, slug, title, and parent.
        Returns the response from the request.
        """
        page_data = self.get_new_page_data()
        page_data.update({
            'template': template,
            'site': self.site.pk,
            'slug': slug,
            'title': title,
            'parent': parent_id or '',
            'published': False,
        })
        get_last_page = lambda: Page.objects.order_by('-id')[0]
        response = self.client.post(URL_CMS_PAGE_ADD, page_data)
        self.assertRedirects(response, URL_CMS_PAGE)
        last_page = get_last_page()
        self.assertEqual(last_page.site_id, page_data['site'])
        self.assertEqual(last_page.parent_id, parent_id)
        self.assertEqual(last_page.template, page_data['template'])
        self.assertEqual(last_page.get_title(), page_data['title'])
        self.assertEqual(last_page.get_slug(), page_data['slug'])
        return last_page.id


class TestTemplateValidationBaseMixin(object):

    def _site_url(self, site_id=None):
        return self._build_url(Site, site_id)

    def _build_url(self, model, instance_id=None):
        args, url = ((instance_id, ), "admin:%s_%s_change") if instance_id \
            else ((), "admin:%s_%s_add")
        return urlresolvers.reverse(url % (
            model._meta.app_label, model._meta.module_name),
        args=args)

    def _trigger_validation_error_on_site_form(
            self, name, domain, templates, err_key, _id=None):
        url = self._site_url(_id) if _id else self._site_url()
        response = self.client.post(url,
            {'name': name, 'domain': domain, 'templates': templates})
        self.assertEquals(response.status_code, 200)
        self.assertTemplatesFormValidationMessage(err_key, response)

    def assertTemplatesFormValidationMessage(self, error_msg_key, response):
        form = response.context['adminform'].form
        error = form.errors['templates'][0]
        self._matches_error_message(
            error, form.custom_error_messages[error_msg_key])

    def _matches_error_message(self, msg, error_pattern):
        str_pieces = set(re.split('({\d+})', error_pattern)) -\
            set(re.findall('({\d+})', error_pattern))
        for str_piece in str_pieces:
            self.assertTrue(str_piece in msg)


class TestTemplateValidation(TestCase, TestTemplateValidationBaseMixin):

    def setUp(self):
        username = 'test_templates_user'
        try:
            User.objects.get(username__exact=username)
        except User.DoesNotExist:
            User.objects.create_superuser(
                username=username, password='x',
                email='%s@templates.com' % username)
        self.client.login(username=username, password='x')
        session = self.client.session
        session['cms_admin_site'] = 1
        session.save()
        self.client.get('/admin/')

    def _templ_url(self, template_id=None):
        return self._build_url(Template, template_id)

    def assertFormValidationMessage(self, error_msg_key, response):
        form = response.context['adminform'].form
        error = form.errors['__all__'][0]
        self._matches_error_message(
            error, form.custom_error_messages[error_msg_key])

    def _trigger_validation_error_on_template_form(
            self, name, content, sites, err_key, _id=None):
        url = self._templ_url(_id) if _id else self._templ_url()
        response = self.client.post(url,
            {'name': name, 'content': content, 'sites': sites})
        self.assertEquals(response.status_code, 200)
        self.assertFormValidationMessage(err_key, response)

    def _update_template(self, name, content, sites, _id=None):
        from datetime import datetime
        _date = datetime.now()
        url = self._templ_url(_id) if _id else self._templ_url()
        response = self.client.post(url,
            {'name': name, 'content': content, 'sites': sites,
             'creation_date_0': ('2012-02-01'),
             'creation_date_1': ('11:43:40'),
             'last_changed_0': (_date.strftime("%Y-%m-%d")),
             'last_changed_1': (_date.strftime("%H:%M:%S"))})
        self.assertEquals(response.status_code, 302)

    def test_syntax_error(self):
        self._trigger_validation_error_on_template_form(
            'templA', '{% dummy %}', [1], 'syntax_error')
        self._update_template('templA', 'random text', [1])

        templA = Template.objects.get(name='templA')
        templA.content = '{% dummy %}'
        templA.save()

        # syntax error in included template
        self._trigger_validation_error_on_template_form(
            'templB', '{% extends "templA" %}', [1], 'syntax_error')
        # syntax error in extended template
        self._trigger_validation_error_on_template_form(
            'templB', '{% include "templA" %}', [1], 'syntax_error')

        templC = Template.objects.create(
            name='templC',
            content=(''
                '{% load sekizai_tags %}'
                '{% render_block "stuff" %}'
                     )
            )
        templC.sites.add(Site.objects.get(id=1))
        templC.save()
        # syntax error in render block
        self._trigger_validation_error_on_template_form(
            'templB',
            ('{% extends "templC" %}'
            '{% load sekizai_tags %}'
            '{% addtoblock "stuff" %}'
            '{% include "templA" %}'
            '{% endaddtoblock %}'), [1], 'syntax_error')

        # syntax error in regular block
        templC.content = (''
            '{% block content %}'
            'some content'
            '{% endblock content %}')
        templC.save()

        self._trigger_validation_error_on_template_form(
            'templB',
            ('{% extends "templC" %}'
            '{% block content %}'
            '{% include "templA" %}'
            '{% endblock content %}'), [1], 'syntax_error')

        # syntax error in super block
        templC.content = (''
            '{% block content %}'
            '{% include "templA" %}'
            '{% endblock content %}')
        templC.save()

        self._trigger_validation_error_on_template_form(
            'templB',
            ('{% extends "templC" %}'
            '{% block content %}'
            '{{ block.super }}'
            '{% endblock content %}'), [1], 'syntax_error')

        # syntax error even when override
        self._trigger_validation_error_on_template_form(
            'templB',
            ('{% extends "templC" %}'
            '{% block content %}'
            'some content'
            '{% endblock content %}'), [1], 'syntax_error')

    def test_name_field_read_only(self):
        response = self.client.get(self._templ_url())
        name_widget = response.context['adminform'].form.fields['name'].widget
        self.assertNotIn('readonly', name_widget.attrs)
        templA = Template.objects.create(
            name='templA', content="asdasd")
        templA.sites.add(Site.objects.get(id=1))
        templA.save()

        response = self.client.get(self._templ_url(templA.id))
        name_widget = response.context['adminform'].form.fields['name'].widget
        self.assertIn('readonly', name_widget.attrs)

    def test_nonexistent_template_use(self):
        self._trigger_validation_error_on_template_form(
            'templB', '{% include "templA" %}', [1], 'missing_template_use')
        self._trigger_validation_error_on_template_form(
            'templB', '{% extends "templA" %}', [1], 'missing_template_use')

        templA = Template.objects.create(name='templA', content=(''
                '{% include "templC" %}'))
        templA.sites.add(Site.objects.get(id=1))
        templA.save()

        self._trigger_validation_error_on_template_form(
            'templB', '{% include "templA" %}', [1], 'missing_template_use')
        self._trigger_validation_error_on_template_form(
            'templB', '{% extends "templA" %}', [1], 'missing_template_use')

        templA.content = (
            '{% block content %}'
            '{% include "templC" %}'
            '{% endblock content %}')
        templA.save()

        self._trigger_validation_error_on_template_form(
            'templB', '{% include "templA" %}', [1], 'missing_template_use')
        self._trigger_validation_error_on_template_form(
            'templB', (
                '{% extends "templA" %}'
                '{% block content %}'
                'texttexttext'
                '{% endblock content %}'), [1], 'missing_template_use')

        templA.content = (
            '{% load sekizai_tags %}'
            '{% render_block "stuff" %}')
        templA.save()

        self._trigger_validation_error_on_template_form(
            'templB', (
                '{% extends "templA" %}'
                '{% load sekizai_tags %}'
                '{% addtoblock "stuff" %}'
                '{% include "templC" %}'
                '{% endaddtoblock %}'), [1], 'missing_template_use')

    def test_templates_use_sites_assigned(self):
        templA = Template.objects.create(name='templA')
        templA.content = 'content'
        templA.save()
        templA.sites.clear()

        templB = Template.objects.create(name='templB')
        templB.content = '{% include "templA" %}'
        templB.save()
        templB.sites.clear()

        self._trigger_validation_error_on_template_form(
            'templC', '{% extends "templB" %}', [1], 'missing_sites')

    def test_sites_unassigned(self):
        siteA = Site.objects.create(name="siteA", domain="siteA")

        templA = Template.objects.create(name='templA')
        templA.content = 'content'
        templA.save()
        templA.sites.add(siteA)

        p = Page(template="templA", site=siteA)
        p.save()

        self._trigger_validation_error_on_template_form(
            'templA', 'content', [1], 'page_use', templA.id)
        self._update_template(
            'templA', 'content', [1, siteA.id], templA.id)

        Page.objects.filter(id=p.id).update(template='templNonExistent')

        self._trigger_validation_error_on_template_form(
            'templA', 'content', [1], 'nonexistent_in_pages', templA.id)

        templB = Template.objects.create(name='templB')
        templB.content = '{% invalid_tag %}'
        templB.save()
        templB.sites.add(siteA)

        Page.objects.filter(id=p.id).update(template='templB')

        self._trigger_validation_error_on_template_form(
            'templA', 'content', [1], 'syntax_error_unassigning', templA.id)

        templC = Template.objects.create(name='templC')
        templC.content = '{% include "NonExistent" %}'
        templC.save()
        templC.sites.add(siteA)

        templB.content = '{% extends "templC" %}'
        templB.save()

        Page.objects.filter(id=p.id).update(template='templB')

        self._trigger_validation_error_on_template_form(
            'templA', 'content', [1], 'missing_template_use', templA.id)

        templC.content = '{% include "templA" %}'
        templC.save()

        self._trigger_validation_error_on_template_form(
            'templA', 'content', [1], 'page_template_use', templA.id)

        templD = Template.objects.create(name='templD')
        templD.content = 'content'
        templD.save()
        templD.sites.add(siteA)

        Page.objects.filter(id=p.id).update(template='templD')

        self._trigger_validation_error_on_template_form(
            'templA', 'content', [1], 'site_template_use', templA.id)

        templB.content = '{% extends "templC" %}{% invalid_tag %}'
        templB.save()

        self._trigger_validation_error_on_template_form(
            'templA', 'content', [1], 'syntax_error_unassigning', templA.id)

        templB.content = '{% extends "templC" %}{% include "NonExistent" %}'
        templB.save()

        self._trigger_validation_error_on_template_form(
            'templA', 'content', [1], 'missing_template_use', templA.id)

        p.delete()
        self._trigger_validation_error_on_template_form(
            'templA', 'content', [1], 'missing_template_use', templA.id)

    def test_site_has_all_templates_required(self):
        created = []
        for t_name in ['templA', 'templB', 'templC', 'templD']:
            templ = Template.objects.create(name=t_name)
            templ.content = "content"
            templ.save()
            created.append(templ)
        templA, templB, templC, templD = tuple(created)

        templA.content = '{% extends "templB" %}'
        templB.content = '{% include "templC" %}'
        templC.content = 'content'

        for t_instance in [templA, templB, templC]:
            t_instance.save()

        self._trigger_validation_error_on_site_form(
            "siteA", "siteA.com", [templA.id], 'all_required')

        s = Site.objects.get(id=1)

        self._trigger_validation_error_on_site_form(
            s.name, s.domain, [templA.id], 'all_required', s.id)

        templC.content = '{% invalid_tag %}'
        templC.save()

        self._trigger_validation_error_on_site_form(
            s.name, s.domain, [templA.id], 'syntax_error', s.id)

        templC.content = '{% extends "NonExistent" %}'
        templC.save()

        self._trigger_validation_error_on_site_form(
            s.name, s.domain, [templA.id], 'required_not_exist', s.id)

        templC.content = 'content'
        templC.save()

        p = Page(template="templD", site=s)
        p.save()

        self._trigger_validation_error_on_site_form(
            s.name, s.domain, [templA.id, templB.id, templC.id],
            'required_in_pages', s.id)

        templD.sites.clear()

        self._trigger_validation_error_on_site_form(
            s.name, s.domain, [templA.id, templB.id, templC.id],
            'required_in_pages', s.id)

        Page.objects.filter(id=p.id).update(template='NonExistent')

        self._trigger_validation_error_on_site_form(
            s.name, s.domain, [templA.id, templB.id, templC.id],
            'nonexistent_in_pages', s.id)

        Page.objects.filter(id=p.id).update(template='templA')

        templD.sites.add(s)

        self._trigger_validation_error_on_site_form(
            s.name, s.domain, [templA.id, templB.id, templC.id],
            'orphan', s.id)

    def _test_menu_tag_template(self, tag_expression):
        templ_menu = Template.objects.create(name='menu')
        templ_menu.content = "{% load menu_tags %}" + tag_expression
        templ_menu.save()

        templ_sub_menu = Template.objects.create(name='sub-menu')
        templ_sub_menu.content = "content"
        templ_sub_menu.save()

        s = Site.objects.get(id=1)
        p = Page(template="menu", site=s)
        p.save()

        self._trigger_validation_error_on_site_form(
            s.name, s.domain, [templ_menu.id],
            'all_required', s.id)

    def test_show_menu_tag_template(self):
        self._test_menu_tag_template("{% show_menu 0 100 100 100 'sub-menu' %}")

    def test_show_sub_menu_tag_template(self):
        self._test_menu_tag_template("{% show_sub_menu 1 'sub-menu' %}")

    def test_show_breadcrumb_tag_template(self):
        self._test_menu_tag_template("{% show_breadcrumb 2 'sub-menu' %}")

    def test_menu_and_sub_menu_tag_template(self):
        s = Site.objects.get(id=1)

        templ_menu = Template.objects.create(name='menu')
        templ_menu.content = "{% load menu_tags %} {% show_menu 0 100 100 100 'sub-menu' %}"
        templ_menu.save()

        templ_sub_menu = Template.objects.create(name='sub-menu')
        templ_sub_menu.content = "{% load menu_tags %} {% show_menu 0 100 100 100 'sub-sub-menu' %}"
        templ_sub_menu.save()
        templ_sub_menu.sites.add(s)

        templ_sub_sub_menu = Template.objects.create(name='sub-sub-menu')
        templ_sub_sub_menu.content = "content"
        templ_sub_sub_menu.save()

        p = Page(template="menu", site=s)
        p.save()

        self._trigger_validation_error_on_site_form(
            s.name, s.domain, [templ_menu.id, templ_sub_menu.id],
            'all_required', s.id)


    def test_empty_menu_tags_template(self):
        templ_menu = Template.objects.create(name='menu')
        templ_menu.content = """
           {% load menu_tags %}
           <html>
           <head>
           </head>
           <body>
           {% show_menu %}
           {% show_sub_menu 1 %}
           {% show_menu_below_id "meta" %}
           {% show_breadcrumb %}
           </body>
           </html>
        """
        templ_menu.save()

        s = Site.objects.get(id=1)
        p = Page(template="menu", site=s)
        p.save()

        url = self._site_url()
        response = self.client.post(url,
            {'name': s.name, 'domain': s.domain, 'templates': [templ_menu.id]})
        self.assertEquals(response.status_code, 302)


class InfiniteRecursivityErrorTest(TestCase):

    tpl1 = """
    {% load menu_tags %}
    {% show_menu 0 100 100 100 "tpl4" %}
    """

    tpl2 = """
    {% extends "tpl1" %}
    """

    tpl3 = """
    {% include "tpl2" %}
    """

    tpl4 = """
    {% extends "tpl3" %}
    """

    def test(self):
        t1 = Template.objects.create(name="tpl1", \
                            content=InfiniteRecursivityErrorTest.tpl1)
        t2 = Template.objects.create(name="tpl2", \
                            content=InfiniteRecursivityErrorTest.tpl2)
        t3 = Template.objects.create(name="tpl3", \
                            content=InfiniteRecursivityErrorTest.tpl3)
        t4 = Template.objects.create(name="tpl4", \
                            content=InfiniteRecursivityErrorTest.tpl4)

        self.assertRaises(InfiniteRecursivityError,
                          handle_recursive_calls, t1.name, t1.content)
        try:
            handle_recursive_calls(t1.name, t1.content)
        except InfiniteRecursivityError, e:
            self.assertEqual(set([u'tpl1', u'tpl2', u'tpl3', u'tpl4']), \
                                     set(e.cycle_items))
