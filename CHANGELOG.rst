CHANGELOG
=========

Revision 08f8ffe (20.10.2015, 13:17 UTC)
----------------------------------------

* LUN-2702

  * django1.8 Handled new exception thrown by django.contrib.sites.models.SiteManager.

* Misc commits

  * Update setup.py

Revision 6724c54 (13.10.2015, 11:54 UTC)
----------------------------------------

* LUN-2706

  * Mock the context.
  * We cannot mock the context, so handle the error as an invalid template.

No other commits.

Revision 6ff5d78 (23.09.2015, 15:31 UTC)
----------------------------------------

No new issues.

* Misc commits

  * Django 1.8: updated templates
  * Django 1.8 upgrade: removed some django1.9 deprecation warnings
  * Django 1.8 upgrade: fixed tests; changed tests settings;

Revision b049980 (04.09.2015, 09:02 UTC)
----------------------------------------

* LUN-2596

  * fieldset columns widths updated

No other commits.

Revision b676c3b (28.08.2015, 07:21 UTC)
----------------------------------------

* LUN-2310

  * updated if condition for tooltip to appear
  * messages wrapper appears only if there are messages
  * remaining of fieldset classes
  * updates for Ace theme on fieldset
  * breadcrumbs updated

No other commits.

Revision 05c2e01 (30.07.2015, 09:08 UTC)
----------------------------------------

No new issues.

* Misc commits

  * Django 1.7 upgrade: updated admin template form focus() call

Revision 45d9308 (17.07.2015, 13:45 UTC)
----------------------------------------

No new issues.

* Misc commits

  * tox: Don't allow django 1.8 prereleases
  * Django 1.7 upgrade; updated template analyzer based on cms&sekizai changes; fixed tests; added django migrations
  * Django 1.6 upgrade: fixed imports & empty qs

Revision 8bc3dcc (06.05.2015, 06:38 UTC)
----------------------------------------

No new issues.

* Misc commits

  * CMS_TEMPLATES needs only template names. No need to pull template content from db

Revision 47de751 (21.10.2014, 11:25 UTC)
----------------------------------------

* LUN-1869

  * Update middleware.py
  * Small improvement
  * Set CMS_TEMPLATES only on exceptional case in SiteIdPatchMiddleware and don't care about interfering in the exception flow (a 404 could possibly be transformed into a 500)
  * Since we are managing the state of the current site id, it is important to sync the CMS_TEMPLATES variables as sooner as possible in the request/response cycle, so that even on early middleware chain breaking, the error page will be displayed correctly with respect to the current site. This fix also ensures that we are able to show the CMS error page even if there is an early exception raised in the middleware chain

* Misc commits

  * Set the default CMS_TEMPLATES at the beginning
  * Update middleware.py

Revision e5ba630 (09.09.2014, 13:04 UTC)
----------------------------------------

* LUN-1805

  * allow other permission checks than the ones from cms.

No other commits.

Revision d736ea9 (07.08.2014, 07:13 UTC)
----------------------------------------

No new issues.

* Misc commits

  * Refactor: CMS_TEMPLATES is locally initialized.
  * Remove CMS_TEMPLATES shorthand ...

Revision 4c5bd0a (23.06.2014, 08:26 UTC)
----------------------------------------

No new issues.

* Misc commits

  * Allow user without roles to logout and change pwd.
  * Dissalow user without roles from any model admin.
  * change site to current only if allowed

Revision a271953 (13.06.2014, 12:04 UTC)
----------------------------------------

* LUN-1544

  * Some small refactoring
  * If the current site (active site of a certain session) is deleted by another user, the user needs to be notified in a nice way (HTTP 404) that the site is not there anymore

No other commits.

Revision 782190b (17.04.2014, 13:20 UTC)
----------------------------------------

Changelog history starts here.
