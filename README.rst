Global Settings
===============

Terms:

DBT = DB Template
Chosen Template List = Can be seen by accessing http://localhost:8000/admin/sites/site/40/,
                       where 40 is the id of a particular site, can be any valid id
		       It represents the list with selected DBTs for the current site
		       (the right one).
DBT List = Can be seen by following: http://localhost:8000/admin/dbtemplates/template
Template drop down = while editing a page, this is the drop down which allows templates to
                      be selected for that page.


There are three configuration variables available:

* ``DBTEMPLATES_INCLUDE_ORPHAN`` a boolean flag that defaults to
  ``True``. If this option is enabled, selecting a site in the
  db template creation form is optional. If a DBT doesn't
  belong to any site it will behave as global and will be available
  in all sites. If set to ``False`` the user will be forced to link
  the DBT that he creates to at least one site.

  A DBT can become orphan if all its sites have been deleted. This
  setting controls if orphan DBTs can be displayed in DBT List
  or to be available for Template drop down.

* ``DBTEMPLATES_RESTRICT_USER`` a boolean flag that defaults to
  ``False``. This flag, if set, will limit the template that
  a user can access based on his relation to sites trough the global
  pages permission system. This can be useful in a shared environment.
  By default a user can access all the DBTs in the system.

  If this setting is True the current user will only have access
  to DBTs which are assigned to sites on which he as
  global page permissions. Otherwise the user will have acess to
  all DBTs.

  For example, if the current user has global page permissions for
  Site1, Site2 and Site3, he will be allowed to edit DBTs which belong
  to these three sites.
