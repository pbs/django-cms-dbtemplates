from django.conf import settings

shared_sites = getattr(settings, 'DBTEMPLATES_SHARED_SITES', [])
include_orphan = getattr(settings, 'DBTEMPLATES_INCLUDE_ORPHAN', False)
restrict_user = getattr(settings, 'DBTEMPLATES_RESTRICT_USER', False)
