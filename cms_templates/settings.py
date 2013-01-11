from django.conf import settings

shared_sites = getattr(settings, 'TEMPLATES_SHARED_SITES', [])
include_orphan = getattr(settings, 'TEMPLATES_INCLUDE_ORPHAN', True)
restrict_user = getattr(settings, 'TEMPLATES_RESTRICT_USER', False)
