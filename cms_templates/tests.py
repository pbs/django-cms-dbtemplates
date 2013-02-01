
from django.test import TestCase
from dbtemplates.models import Template
from django.contrib.sites.models import Site
from django.contrib.auth.models import User, Group
from cms.models.permissionmodels import GlobalPagePermission
from django.contrib.admin.options import ModelAdmin
from django.test.client import RequestFactory
from django.core import urlresolvers

from django_dynamic_fixture import G, get

from restricted_admin_decorators import restricted_has_delete_permission, restricted_get_readonly_fields, restricted_formfield_for_manytomany, restricted_queryset


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
        Site.objects.all().delete() # delete example.com
        self.main_user = G(User)
        self.site1 = G(Site)
        self.site2 = G(Site)
        self.site3 = G(Site)
        self.template = G(Template, sites=[self.site1, self.site2, self.site3])
        self.request = RequestFactory().get(self._admin_url(self.template))

    def tearDown(self):
        #flush db
        super(TestCase, self)._fixture_setup()

    def test_formfield_m2m_no_restrict_user(self):

        @restricted_formfield_for_manytomany(restrict_user=False)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        setattr(self.request, 'user', self.main_user)
        gpp = G(GlobalPagePermission, sites=[self.site1, self.site2], user=self.main_user)
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
        user2 = G(User)
        gpp1 = G(GlobalPagePermission, sites=[self.site1], user=self.main_user)
        gpp2 = G(GlobalPagePermission, sites=[self.site2], user=user2)
        dma = DecoratedModelAdmin(Template, admin_site=None)
        
        dma.formfield_for_manytomany(self.db_field, self.request)
        
        self.assertQuerysetEqual(dma._test_sites,
                                      [self.site1.id],
                                      lambda o : o.id)

    def test_formfield_m2m_restrict_user_and_user_in_group(self):

        @restricted_formfield_for_manytomany(restrict_user=True)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass
        
        User.objects.all().delete()
        group1 = G(Group)
        group2 = G(Group)
        self.main_user = G(User, groups=[group1])
        setattr(self.request, 'user', self.main_user)
        user2 = G(User, groups=[group2])
        gpp1= G(GlobalPagePermission, sites=[self.site1], group = group1)
        gpp2= G(GlobalPagePermission, sites=[self.site2], group = group2)
        dma = DecoratedModelAdmin(Template, admin_site=None)
        
        dma.formfield_for_manytomany(self.db_field, self.request)
        
        self.assertQuerysetEqual(dma._test_sites,
                                 [self.site1.id],
                                 lambda o : o.id)


    def test_queryset1(self):
        @restricted_queryset(False, (), False)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        tpl2 = G(Template, sites=[self.site1, self.site2, self.site3])
        tpl3 = G(Template, sites=[self.site1, self.site2, self.site3])
        tpl4 = G(Template, sites=[self.site1, self.site2, self.site3])
        
        setattr(self.request, 'user', self.main_user)
        gpp1 = G(GlobalPagePermission, sites=[self.site1], user=self.main_user)
        dma = DecoratedModelAdmin(Template, admin_site=None)

        self.assertQuerysetEqual(dma.queryset(self.request),
                                 [self.template.id, tpl2.id, tpl3.id, tpl4.id],
                                 lambda o: o.id, ordered=False)
        
        
    def test_queryset2(self):

        @restricted_queryset(restrict_user=True, shared_sites=(), include_orphan=False)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        tpl2 = G(Template, sites=[self.site2, self.site3])
        tpl3 = G(Template, sites=[self.site3])
        
        setattr(self.request, 'user', self.main_user)
        gpp1 = G(GlobalPagePermission, sites=[self.site1], user=self.main_user)
        dma = DecoratedModelAdmin(Template, admin_site=None)

        self.assertQuerysetEqual(dma.queryset(self.request),
                                 [self.template.id],
                                 lambda o: o.id)

    def test_queryset4(self):
        @restricted_queryset(restrict_user=True, shared_sites=(), include_orphan=False)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        tpl2 = G(Template, sites=[self.site2, self.site3])
        tpl3 = G(Template, sites=[self.site3])

        group1 = G(Group)
        self.main_user = G(User, groups=[group1])
        setattr(self.request, 'user', self.main_user)
        
        setattr(self.request, 'user', self.main_user)
        gpp1 = G(GlobalPagePermission, sites=[self.site1], group=group1)
        dma = DecoratedModelAdmin(Template, admin_site=None)

        self.assertQuerysetEqual(dma.queryset(self.request),
                                 [self.template.id],
                                 lambda o: o.id)

    def test_queryset5(self):
        @restricted_queryset(restrict_user=False, shared_sites=(self.site1.name, ), include_orphan=False)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        tpl2 = G(Template, sites=[self.site2, self.site3])
        tpl3 = G(Template, sites=[self.site1, self.site3])

        group1 = G(Group)
        self.main_user = G(User, groups=[group1])
        setattr(self.request, 'user', self.main_user)
        
        gpp1 = G(GlobalPagePermission, sites=[self.site1], group=group1)
        dma = DecoratedModelAdmin(Template, admin_site=None)

        self.assertQuerysetEqual(dma.queryset(self.request),
                                 [self.template.id, tpl3.id],
                                 lambda o: o.id, ordered=False)

    def test_queryset6(self):
        @restricted_queryset(restrict_user=False, shared_sites=(), include_orphan=True)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        tpl2 = G(Template, sites=[self.site2, self.site3])
        tpl3 = G(Template, sites=[]) #this is an orphan template

        group1 = G(Group)
        self.main_user = G(User, groups=[group1])
        setattr(self.request, 'user', self.main_user)
        
        gpp1 = G(GlobalPagePermission, sites=[self.site1], group=group1)
        dma = DecoratedModelAdmin(Template, admin_site=None)

        self.assertQuerysetEqual(dma.queryset(self.request),
                                 [tpl3.id],
                                 lambda o: o.id)

    def test_get_readonly_fields1(self):
        ro=('a', 'b', 'c')
        allways=('e', 'f', 'g')
        @restricted_get_readonly_fields(restrict_user=False, shared_sites=(), ro=ro, allways=allways)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        setattr(self.request, 'user', self.main_user)
        
        dma = DecoratedModelAdmin(Template, admin_site=None)

        self.assertEquals(dma.get_readonly_fields(self.request), allways)

    def test_get_readonly_fields2(self):
        ro=('a', 'b', 'c')
        allways=('e', 'f', 'g')
        @restricted_get_readonly_fields(restrict_user=False, shared_sites=(), ro=ro, allways=allways)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        setattr(self.request, 'user', self.main_user)
        
        dma = DecoratedModelAdmin(Template, admin_site=None)

        self.assertEquals(dma.get_readonly_fields(self.request, self.template), allways)

    def test_get_readonly_fields3(self):
        ro=('a', 'b', 'c')
        allways=('e', 'f', 'g')
        @restricted_get_readonly_fields(restrict_user=True, shared_sites=(self.site1, ), ro=ro, allways=allways)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        setattr(self.request, 'user', self.main_user)
        
        dma = DecoratedModelAdmin(Template, admin_site=None)

        self.assertEquals(dma.get_readonly_fields(self.request, self.template), ro)

    def test_get_readonly_fields4(self):
        ro=('a', 'b', 'c')
        allways=('e', 'f', 'g')
        site4 = G(Site)
        @restricted_get_readonly_fields(restrict_user=True, shared_sites=(site4, ), ro=ro, allways=allways)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        setattr(self.request, 'user', self.main_user)
        
        dma = DecoratedModelAdmin(Template, admin_site=None)

        self.assertEquals(dma.get_readonly_fields(self.request, self.template), allways)

        
    def test_has_delete_permission1(self):
        @restricted_has_delete_permission(restrict_user=True, shared_sites=())
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        setattr(self.request, 'user', self.main_user)
        
        dma = DecoratedModelAdmin(Template, admin_site=None)

        self.assertEquals(dma.has_delete_permission(self.request), True)

    def test_has_delete_permission2(self):
        site4 = G(Site)
        @restricted_has_delete_permission(restrict_user=True, shared_sites=(site4, ))
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        setattr(self.request, 'user', self.main_user)
        
        dma = DecoratedModelAdmin(Template, admin_site=None)

        self.assertEquals(dma.has_delete_permission(self.request, self.template), True)

    def test_has_delete_permission3(self):
        @restricted_has_delete_permission(restrict_user=True, shared_sites=(self.site1, ))
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        setattr(self.request, 'user', self.main_user)
        
        dma = DecoratedModelAdmin(Template, admin_site=None)

        self.assertEquals(dma.has_delete_permission(self.request, self.template), False)


from django.conf import settings as django_settings
from django.contrib.sites.models import Site
from django.template import loader, Context, TemplateDoesNotExist
from mock import patch

class TestLoader(TestCase):

    def tearDown(self):
        #flush db
        super(TestCase, self)._fixture_setup()

    
    def test_shared_site_template(self):
        with patch('cms_templates.loader.shared_sites') as mock:
            mock.return_value = ['SHARED_SITE']
        
            shared_site = Site.objects.create(domain="shared_site.org", name="SHARED_SITE")
            site1 = Site.objects.create(domain="site1.org", name="site1")
            site2 = Site.objects.create(domain="site2.org", name="site2")
        
            t1_shared = Template.objects.create(name='shared.html', content='shared')
            t1_shared.sites.add(shared_site)

            t1_s1 = Template.objects.create(name='site1.html', content='site1')
            t1_s1.sites.add(site1)        
        
            t2_s2 = Template.objects.create(name='site2.html', content='site2')
            t2_s2.sites.add(site2)
                                  
            django_settings.SITE_ID = site1.id
            tpl = loader.get_template('site1.html')
            self.assertEqual(tpl.render(Context({})), 'site1')
            #test that template assigned to the shared site (SHARED_SITE) is available for site1
            tpl = loader.get_template('shared.html')
            self.assertEqual(tpl.render(Context({})), 'shared')
            self.assertRaises(TemplateDoesNotExist, loader.get_template, "site2.html")
                                  
            django_settings.SITE_ID = site2.id
            tpl = loader.get_template('site2.html')
            self.assertEqual(tpl.render(Context({})), 'site2')
            #test that template assigned to the shared site (SHARED_SITE) is available for site2
            tpl = loader.get_template('shared.html')
            self.assertEqual(tpl.render(Context({})), 'shared')
            self.assertRaises(TemplateDoesNotExist, loader.get_template, "site1.html")
            
    def test_shared_template_assigned_also_to_another_site(self):
        #test that no exception is raised because the shared template belongs to both shared site and site1
        with patch('cms_templates.loader.shared_sites') as mock:
            mock.return_value = ['SHARED_SITE']
        
            shared_site = Site.objects.create(domain="shared_site.org", name="SHARED_SITE")
            site1 = Site.objects.create(domain="site1.org", name="site1")

            django_settings.SITE_ID = site1.id
            
            t1_shared = Template.objects.create(name='shared.html', content='shared')
            #shared template belongs to both sites
            t1_shared.sites.add(shared_site, site1)

            t1_s1 = Template.objects.create(name='site1.html', content='site1')
            t1_s1.sites.add(site1)        

            tpl = loader.get_template('shared.html')
            self.assertEqual(tpl.render(Context({})), 'shared')
            
    def test_orphan(self):
        #test that the orphan site can be loaded
        site1 = Site.objects.create(domain="site1.org", name="site1")

        django_settings.SITE_ID = site1.id
        t_orphan = Template.objects.create(name='orphan.html', content='orphan')

        self.assertEqual(loader.get_template('orphan.html').render(Context({})), 'orphan')
