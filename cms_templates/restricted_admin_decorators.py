from django.contrib.sites.models import Site
from django.db.models import Q
from django.contrib.admin.options import ModelAdmin

def throw_error_if_not_ModelAdmin(f):
    def _inner(*args, **kwargs):
        cls = args[0]
        if not issubclass(cls, ModelAdmin):
            raise TypeError('%s should be an subclass of ModelAdmin' % cls.__name__)
        return f(*args, **kwargs)
    return _inner

def restricted_formfield_for_manytomany(restrict_user=False, **kw):
    """Parameterized class decorator used to extend the default "formfield_for_manytomany" behavior of a ModelAdmin derived class.
    """
    @throw_error_if_not_ModelAdmin
    def _formfield_for_manytomany(cls):
        
        def __formfield_for_manytomany(self, db_field, request, **kwargs):
            if db_field.name == "sites":
                f = Q()
                if not request.user.is_superuser:
                    if restrict_user:
                        f |= Q(globalpagepermission__user=request.user)
                        f |= Q(globalpagepermission__group__user=request.user)
                kwargs["queryset"] = Site.objects.filter(f).distinct()
            return (super(cls, self)
                    .formfield_for_manytomany(db_field, request, **kwargs))

        cls.formfield_for_manytomany = __formfield_for_manytomany
        return cls
    return _formfield_for_manytomany

def restricted_queryset(restrict_user=False, shared_sites=(), include_orphan=True, **kw):
    """Parameterized class decorator used to extend the default "queryset" behavior of a ModelAdmin derived class.
    """
    @throw_error_if_not_ModelAdmin
    def _queryset(cls):

        def __queryset(self, request):
            q = super(cls, self).queryset(request)
            f = Q()
            if not request.user.is_superuser:
                if restrict_user:
                    f |= Q(sites__globalpagepermission__user=request.user)
                    f |= Q(sites__globalpagepermission__group__user=request.user)
                if shared_sites:
                    f |= Q(sites__name__in=shared_sites)
                if include_orphan:
                    f |= Q(sites__isnull=True)
            return q.filter(f).distinct()

        cls.queryset = __queryset
        return cls
        
    return _queryset


def restricted_get_readonly_fields(restrict_user=False, shared_sites=(), ro=(), allways=(), **kw):
    """Parameterized class decorator used to extend the default "get_readonly_fields" behavior of a ModelAdmin derived class.
    """
    @throw_error_if_not_ModelAdmin
    def _get_readonly_fields(cls):

        def __get_readonly_fields(self, request, obj=None):
            if not obj or request.user.is_superuser:
                return allways
            if restrict_user and shared_sites:
                if obj.sites.filter(name__in=shared_sites):
                    return ro
            return allways
            
        cls.get_readonly_fields = __get_readonly_fields
        return cls
        
    return _get_readonly_fields

def restricted_has_delete_permission(restrict_user=False, shared_sites=(), **kw):
    """Parameterized class decorator used to extend the default "has_delete_permission" behavior of a ModelAdmin derived class.
    """
    @throw_error_if_not_ModelAdmin
    def _has_delete_permission(cls):

        def __has_delete_permission(self, request, obj=None):
            if request.user.is_superuser or obj is None:
                return True
            if restrict_user and shared_sites:
                return not bool(obj.sites.filter(name__in=shared_sites))
            return True

        cls.has_delete_permission = __has_delete_permission
        return cls
    return _has_delete_permission

def restricted_change_view(restrict_user=False, shared_sites=(), **kw):
    """Parameterized class decorator used to extend the default "change_view" behavior of a ModelAdmin derived class.
    """
    @throw_error_if_not_ModelAdmin
    def _change_view(cls):
        
        def __change_view(self, request, object_id, extra_context=None):
            extra_context = {}
            if not request.user.is_superuser:
                if restrict_user and shared_sites:
                    m = self.model.objects.get(pk=object_id)
                    if m.sites.filter(name__in=shared_sites):
                        extra_context = {'read_only': True}
            return super(cls, self).change_view(request,
                        object_id, extra_context=extra_context)
            
        cls.change_view = __change_view
        return cls
    return _change_view


