
from django.test import TestCase
from dbtemplates.models import Template
from django.contrib.sites.models import Site
from django.contrib.auth.models import User, Group
from cms.models.permissionmodels import GlobalPagePermission
from django.contrib.admin.options import ModelAdmin
from django.test.client import RequestFactory
from django.core import urlresolvers
from django.conf import settings as django_settings

from restricted_admin_decorators import restricted_has_delete_permission, restricted_get_readonly_fields, restricted_formfield_for_manytomany, restricted_queryset

counter = 0
def create_site(**kwargs):
    global counter
    counter = counter + 1
    defaults = {
        "domain": "domain%d.org" % counter,
        "name": "site%d" % counter,
        }
    defaults.update(kwargs)
    return Site.objects.create(**defaults)

def create_template(**kwargs):
    global counter
    counter = counter + 1
    defaults = {
        "name": "template%d" % counter,
        "content": "content%d" % counter,
        }
    sites = []
    if "sites" in kwargs:
        sites = kwargs["sites"]
        del kwargs["sites"]
    defaults.update(kwargs)
    t = Template(**defaults)
    t.save()
    t.sites = sites
    return t


def create_user(**kwargs):
    global counter
    counter = counter + 1
    defaults = {
        "username": "username%d" % counter,
        "first_name": "user%d" % counter,
        "last_name": "luser%d" % counter,
        "email": "user%d@luser%d.com" % (counter, counter),
        "password": "password%d" % counter,
        }
    groups = []
    if "groups" in kwargs:
        groups = kwargs["groups"]
        del kwargs["groups"]
    user_permissions = []
    if "user_permissions" in kwargs:
        user_permissions = kwargs["user_permissions"]
        del kwargs["user_permissions"]
    defaults.update(kwargs)
    u = User(**defaults)
    u.save()
    u.groups = groups
    u.user_permissions = user_permissions
    return u

def create_group(**kwargs):
    global counter
    counter = counter + 1
    defaults = {
        "name": "group%d" % counter,
        }
    permissions = []
    if "permissions" in kwargs:
        Permissions = kwargs["permissions"]
        del kwargs["permissions"]
    defaults.update(kwargs)
    g = Group(**defaults)
    g.save()
    g.permissions = permissions
    return g


def create_globalpagepermission(**kwargs):
    sites = []
    if "sites" in kwargs:
        sites = kwargs["sites"]
        del kwargs["sites"]
    gpp = GlobalPagePermission(**kwargs)
    gpp.save()
    gpp.sites = sites
    return gpp

class ToBeDecoratedModelAdmin(ModelAdmin):

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        self._test_sites = kwargs['queryset']
        return None    

    def queryset(self, restrict_user=False, shared_sites=[], include_orphan=True, **kw):
        return self.model._default_manager.get_query_set()


class TestDecorators(TestCase):

    def _admin_url(self, template):
        #Returns /admin/dbtemplates/template/1/
        return urlresolvers.reverse("admin:%s_%s_change" % (template._meta.app_label, template._meta.module_name), args=(template.id,))

    def _db_field(self):
        class DbField(object):
            name = 'sites'
        return DbField()
    db_field = property(_db_field)

    def setUp(self):
        Site.objects.all().delete()  # delete example.com
        self.main_user = create_user()
        self.site1 = create_site()
        django_settings.SITE_ID = self.site1.id
        self.site2 = create_site()
        self.site3 = create_site()
        self.template = create_template(sites=[self.site1, self.site2, self.site3])
        self.request = RequestFactory().get(self._admin_url(self.template))

    def tearDown(self):
        #flush db
        super(TestCase, self)._fixture_setup()

    def test_formfield_m2m_no_restrict_user(self):

        @restricted_formfield_for_manytomany(restrict_user=False)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        setattr(self.request, 'user', self.main_user)
        gpp = create_globalpagepermission(sites=[self.site1, self.site2], user=self.main_user)
        dma = DecoratedModelAdmin(Template, admin_site=None)

        dma.formfield_for_manytomany(self.db_field, self.request)

        self.assertQuerysetEqual(dma._test_sites,
                                      [self.site1.id, self.site2.id, self.site3.id],
                                      lambda o: o.id, ordered=False)

    def test_formfield_m2m_restrict_user(self):

        @restricted_formfield_for_manytomany(restrict_user=True)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        setattr(self.request, 'user', self.main_user)
        user2 = create_user()
        gpp1 = create_globalpagepermission(sites=[self.site1], user=self.main_user)
        gpp2 = create_globalpagepermission(sites=[self.site2], user=user2)
        dma = DecoratedModelAdmin(Template, admin_site=None)

        dma.formfield_for_manytomany(self.db_field, self.request)

        self.assertQuerysetEqual(dma._test_sites,
                                      [self.site1.id],
                                      lambda o: o.id)

    def test_formfield_m2m_restrict_user_and_user_in_group(self):

        @restricted_formfield_for_manytomany(restrict_user=True)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        User.objects.all().delete()
        group1 = create_group()
        group2 = create_group()
        self.main_user = create_user(groups=[group1])
        setattr(self.request, 'user', self.main_user)
        user2 = create_user(groups=[group2])
        gpp1= create_globalpagepermission(sites=[self.site1], group=group1)
        gpp2= create_globalpagepermission(sites=[self.site2], group=group2)
        dma = DecoratedModelAdmin(Template, admin_site=None)

        dma.formfield_for_manytomany(self.db_field, self.request)

        self.assertQuerysetEqual(dma._test_sites,
                                 [self.site1.id],
                                 lambda o: o.id)


    def test_queryset1(self):
        @restricted_queryset(False, (), False)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        tpl2 = create_template(sites=[self.site1, self.site2, self.site3])
        tpl3 = create_template(sites=[self.site1, self.site2, self.site3])
        tpl4 = create_template(sites=[self.site1, self.site2, self.site3])

        setattr(self.request, 'user', self.main_user)
        gpp1 = create_globalpagepermission(sites=[self.site1], user=self.main_user)
        dma = DecoratedModelAdmin(Template, admin_site=None)

        self.assertQuerysetEqual(dma.queryset(self.request),
                                 [self.template.id, tpl2.id, tpl3.id, tpl4.id],
                                 lambda o: o.id, ordered=False)


    def test_queryset2(self):

        @restricted_queryset(restrict_user=True, shared_sites=[], include_orphan=False)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass
        tpl2 = create_template(sites=[self.site2, self.site3])
        tpl3 = create_template(sites=[self.site3])

        setattr(self.request, 'user', self.main_user)
        gpp1 = create_globalpagepermission(sites=[self.site1], user=self.main_user)
        dma = DecoratedModelAdmin(Template, admin_site=None)


        self.assertQuerysetEqual(dma.queryset(self.request),
                                 [self.template.id],
                                 lambda o: o.id, ordered=False)

    def test_queryset4(self):
        @restricted_queryset(restrict_user=True, shared_sites=[], include_orphan=False)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        tpl2 = create_template(sites=[self.site2, self.site3])
        tpl3 = create_template(sites=[self.site3])

        group1 = create_group()
        self.main_user = create_user(groups=[group1])
        setattr(self.request, 'user', self.main_user)

        setattr(self.request, 'user', self.main_user)
        gpp1 = create_globalpagepermission(sites=[self.site1], group=group1)
        dma = DecoratedModelAdmin(Template, admin_site=None)

        self.assertQuerysetEqual(dma.queryset(self.request),
                                 [self.template.id],
                                 lambda o: o.id)

    def test_queryset5(self):
        @restricted_queryset(restrict_user=False, shared_sites=[self.site1.name], include_orphan=False)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        tpl2 = create_template(sites=[self.site2, self.site3])
        tpl3 = create_template(sites=[self.site1, self.site3])

        group1 = create_group()
        self.main_user = create_user(groups=[group1])
        setattr(self.request, 'user', self.main_user)

        gpp1 = create_globalpagepermission(sites=[self.site1], group=group1)
        dma = DecoratedModelAdmin(Template, admin_site=None)

        self.assertQuerysetEqual(dma.queryset(self.request),
                                 [self.template.id, tpl3.id],
                                 lambda o: o.id, ordered=False)

    def test_queryset6(self):
        @restricted_queryset(restrict_user=False, shared_sites=[], include_orphan=True)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        tpl2 = create_template(sites=[self.site2, self.site3])
        tpl3 = create_template() #this is an orphan template

        group1 = create_group()
        self.main_user = create_user(groups=[group1])
        setattr(self.request, 'user', self.main_user)

        gpp1 = create_globalpagepermission(sites=[self.site1], group=group1)
        dma = DecoratedModelAdmin(Template, admin_site=None)

        self.assertQuerysetEqual(dma.queryset(self.request),
                                 [tpl3.id],
                                 lambda o: o.id)

    def test_get_readonly_fields1(self):
        ro=('a', 'b', 'c')
        allways=('e', 'f', 'g')
        @restricted_get_readonly_fields(restrict_user=False, shared_sites=[], ro=ro, allways=allways)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        setattr(self.request, 'user', self.main_user)
        
        dma = DecoratedModelAdmin(Template, admin_site=None)

        self.assertEquals(dma.get_readonly_fields(self.request), allways)

    def test_get_readonly_fields2(self):
        ro=('a', 'b', 'c')
        allways=('e', 'f', 'g')
        @restricted_get_readonly_fields(restrict_user=False, shared_sites=[], ro=ro, allways=allways)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        setattr(self.request, 'user', self.main_user)

        dma = DecoratedModelAdmin(Template, admin_site=None)

        self.assertEquals(dma.get_readonly_fields(self.request, self.template), allways)

    def test_get_readonly_fields3(self):
        ro=('a', 'b', 'c')
        allways=('e', 'f', 'g')
        @restricted_get_readonly_fields(restrict_user=True, shared_sites=[self.site1.name], ro=ro, allways=allways)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        setattr(self.request, 'user', self.main_user)

        dma = DecoratedModelAdmin(Template, admin_site=None)

        self.assertEquals(dma.get_readonly_fields(self.request, self.template), ro)

    def test_get_readonly_fields4(self):
        ro = ('a', 'b', 'c')
        allways = ('e', 'f', 'g')
        site4 = create_site()
        @restricted_get_readonly_fields(restrict_user=True, shared_sites=[site4.name], ro=ro, allways=allways)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        setattr(self.request, 'user', self.main_user)

        dma = DecoratedModelAdmin(Template, admin_site=None)

        self.assertEquals(dma.get_readonly_fields(self.request, self.template), allways)


    def test_has_delete_permission1(self):
        @restricted_has_delete_permission(restrict_user=True, shared_sites=[])
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        setattr(self.request, 'user', self.main_user)

        dma = DecoratedModelAdmin(Template, admin_site=None)

        self.assertEquals(dma.has_delete_permission(self.request), True)

    def test_has_delete_permission2(self):
        site4 = create_site()
        @restricted_has_delete_permission(restrict_user=True, shared_sites=[site4.name])
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        setattr(self.request, 'user', self.main_user)

        dma = DecoratedModelAdmin(Template, admin_site=None)

        self.assertEquals(dma.has_delete_permission(self.request, self.template), True)

    def test_has_delete_permission3(self):
        @restricted_has_delete_permission(restrict_user=True, shared_sites=[self.site1.name])
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        setattr(self.request, 'user', self.main_user)

        dma = DecoratedModelAdmin(Template, admin_site=None)

        self.assertEquals(dma.has_delete_permission(self.request, self.template), False)


from django.contrib.sites.models import Site
from django.template import loader, Context, TemplateDoesNotExist
from mock import patch


class TestLoader(TestCase):

    # def tearDown(self):
    #     #flush db
    #     super(TestCase, self)._fixture_setup()

    def test_shared_site_template(self):
        with patch('cms_templates.loader.shared_sites') as mock:
            mock.return_value = ['SHARED_SITE']

            shared_site = Site.objects.create(domain="shared_site.org", name="SHARED_SITE")
            site1 = Site.objects.create(domain="site1.org", name="site1")
            django_settings.SITE_ID = site1.id

            site2 = Site.objects.create(domain="site2.org", name="site2")

            t1_shared = Template.objects.create(name='shared.html', content='shared')
            t1_shared.sites.clear()
            t1_shared.sites.add(shared_site)

            t1_s1 = Template.objects.create(name='site1.html', content='site1')
            t1_s1.sites.clear()
            t1_s1.sites.add(site1)

            t2_s2 = Template.objects.create(name='site2.html', content='site2')
            t2_s2.sites.clear()
            t2_s2.sites.add(site2)

            tpl = loader.get_template('site1.html')
            self.assertEqual(tpl.render(Context({})), 'site1')
            #test that template assigned to the shared site (SHARED_SITE) is available for site1
            tpl = loader.get_template('shared.html')
            self.assertEqual(tpl.render(Context({})), 'shared')

            self.assertRaises(TemplateDoesNotExist, loader.get_template, "site2.html")


    def test_shared_template_assigned_also_to_another_site(self):
        #test that no exception is raised because the shared template belongs to both shared site and site1
        with patch('cms_templates.loader.shared_sites') as mock:
            mock.return_value = ['SHARED_SITE']

            shared_site = Site.objects.create(domain="shared_site.org", name="SHARED_SITE")
            site1 = Site.objects.create(domain="site1.org", name="site1")

            django_settings.SITE_ID = site1.id

            t1_shared = Template.objects.create(name='shared.html', content='shared')
            #shared template belongs to both sites
            t1_shared.sites.clear()
            t1_shared.sites.add(shared_site, site1)

            t1_s1 = Template.objects.create(name='site1.html', content='site1')
            t1_s1.sites.clear()
            t1_s1.sites.add(site1)        

            tpl = loader.get_template('shared.html')
            self.assertEqual(tpl.render(Context({})), 'shared')

    def test_orphan(self):
        #test that the orphan site can be loaded
        site1 = Site.objects.create(domain="site1.org", name="site1")

        django_settings.SITE_ID = site1.id
        t_orphan = Template.objects.create(name='orphan.html', content='orphan')

        self.assertEqual(loader.get_template('orphan.html').render(Context({})), 'orphan')
