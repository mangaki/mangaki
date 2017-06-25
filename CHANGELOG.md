# Mangaki v0.2

# New Features

## Public

- Translate "about us" page (#356) [Jill-Jênn Vie] and [Ryan Lahfa]

- Redesign the profile view (#364) [Ryan Lahfa]

- Add ribbons displaying card category (anime, manga, album) (#362) [Basile Clement]

- Re-design the work cards (#331) [Basile Clement]

- Send templated mail with tokens (#327) [Jill-Jênn Vie]

  For the Kyoto Data Challenge, you should have received emails containing an opt-out link.

- Add link in profile for sorting any wishlist (#326) [Jill-Jênn Vie]

  You can use our algorithms to sort your wishlist (SVD or ALS are available).

- Add attribute research_ok to Profile (#316) [Jill-Jênn Vie]

  Enable people to opt-out from Kyoto Data Science challenge.

- Enable anonymous recommendations [Basile Clement] and [Ryan Lahfa]

  Fixes #59. It allows anonymous users to rate works,
  and keeps the state of the rated works across consecutive page loads
  in Django's session.

  Then, get recommendations (using KNN algorithm).

  Finally, it is possible to sign up and load these ratings in your new account.

  Next step is to handle social login and conflicts when logging in already existing accounts.
  If you rate works anonymously and log in your account, you will lose your anonymous ratings.

  References: #277, #278, #279, #287, #320, #324

- Updated about and events pages (#286) [Jill-Jênn Vie]

## Administration / Development

- Support Sentry (#350) [Ryan Lahfa]

- Better Ansible setup (#321) [Basile Clement]

  This gives a relift to the Ansible setup, allowing several things that
  were not included in the previous setup:

   - Possibility to provision a development machine (e.g. Vagrant box)
   - Possibility to easily dump & restore a database
   - Multi-site deployment (deployments are identified by name; except for
     some global nginx and postgresql configuration that shouldn't change
     anyways, care has been taken to ensure all other settings are
     properly isolated so that several deployments with different
     `mangaki_name` values can co-exist on the same machine)
   - git-free deployment; Mangaki can now be built as a PIP package that
     is copied to the remote machine for installation

  This deployment is implemented as a single playbook that was made as
  declarative as possible; tags and (Ansible's) environment variables
  should be used to run the few actions that should be run (collectstatic,
  dumping or loading a database, etc.)

- Add WorkCluster class for merging works (dedupe, suggestions, or merge
  from admin) (#307) [Jill-Jênn Vie]

- Add an admin interface for merging works (#299) [Jill-Jênn Vie]

# Improvement

## Algorithms

- Add all recommendation algorithms to production (#265) [Jill-Jênn Vie]

  Also, introduced in #268 a new management command `fit_algo` to fit these algorithms locally and save a model.
  Which is refactored in #270.

  References: #265, #268, #270, #276.

## Tests

- Enable AniDB testing through mocking using responses library (#285)
  [Ryan Lahfa]

## Performance

- Reduce the amount of queries for ratings selection (#348) [Ryan Lahfa]

- Improve drastically MAL import performance (#311) [Ryan Lahfa]

- Load all ratings only at fitting time (recommendations) (#340) [Ryan
  Lahfa]

  Now, recommendations should be faster on your local instance.

- Only require tensorflow when needed (#329) [Basile Clement]

  TensorFlow is only required by the WALS algorithm, and loading the
  library has a prohibitive overhead on lower-powered devices. Let's only
  load it when the WALS algorithm is needed, which for now is only when
  running the algorithm, which shouldn't be done on the webserver anyways.

- WorkList: fetch int_poster also to prevent duplicated queries (#295)
  [Ryan Lahfa]

- Views: Select category to prevent duplicated queries (#292) [Ryan
  Lahfa]

## Misc

- House-keeping of gitignore and dependencies (#341) [Ryan Lahfa]
  (bump Django Debug Toolbar to 1.6 and clean the gitignore file)

- Ajout du meta description (#325) [Camille P]

- Upgrade to Django 1.11 (#315) [Basile Clement]

- Reformat and remove useless classes in admin (#294) [Ryan Lahfa]

  Code cleanup.

- Some April cleanup! (#289) [Ryan Lahfa]

  Random cleanup (PEP8, reformatting, etc.)

- Simplify circle-ci integration (#281) [Basile Clement]

- Add a template for settings.ini (#272) [Zeletochoy]

- Requirements: move pandas, sklearn to production due to DPP recent
  introduction (#262) [Ryan Lahfa]

# Fixes

- Make French great again (space before '!' become &nbsp;) (#332) [Ryan
  Lahfa]

- Update seed data (unreviewed) [Basile Clement]

  The seed_data.json was not updated after first_name and last_name were
  removed from Artist. This fixes that.

- Toggling ratings (#306) [Jill-Jênn Vie]

  You may have been unable to "remove" (toggle) a rating, this should be fixed.

- Views: Enforce POST to get CSRF token check and return proper JSON
  (#293) [Ryan Lahfa]

## MAL

- Add a data migration to fix MAL external posters (#347) [Ryan Lahfa]

- Improve MAL usage in Mangaki (#302) [Ryan Lahfa]

  Refactor of MAL module, handle basic alternative titles de-duplication.

- MAL imports (#301) [Ryan Lahfa]

  Some of you may have experienced broken MAL imports, from now on, you should be able to re-import your MAL.
  Some works might still not appear on your profile, e.g. Code Geass: Fukkatsu no Lelouch.
  This will be fixed definitely in 0.3.

## Vagrant

- Use an array rather than string for source_domains on mangaki_dev
  group vars (#352) [Ryan Lahfa]

# Removed since v0.1.4.2

- Kill /users route (#354) [Ryan Lahfa]

- Remove unused test.css file. (#335) [Basile Clement]

- Kill Doctor management command (#333) [Ryan Lahfa]

- Completely remove discourse from Mangaki (#282) [Basile Clement]

  We are not using it anymore. Fixes #264.

- Remove the Profile.score field (#283) [Basile Clement]

  This provides little information (especially considering how cryptic what it
  does is), and the way it is computed gets in the way whenever we want to change
  things relative to ratings.

  Note that it would be easy to add this again if the needs arises as even though
  the value is dynamically updated in various places, it is easy to re-compute it
  from the sets of Suggestions and Recommendations the user submitted.

- Remove first_name and last_name from Artist (#271) [Jill-Jênn Vie]

- Link to meta.mangaki.fr deleted (#266) [Camille P]
