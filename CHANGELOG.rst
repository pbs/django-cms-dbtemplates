CHANGELOG
=========

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
