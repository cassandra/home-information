<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Visual Testing Page

Visit: [http:/tests/ui](http:/tests/ui).

These tests/ui views are only available in the development environment when DEBUG=True. (They are conditionally loaded in the root urls.py.)

## Adding to the Visual Testing Page

The `hi.tests.ui` module uses auto-discovery by looking in the app directories.

In the app direcxtory you want to have a visual testing page:

``` shell
mkdir -p tests/ui
touch tests.__init__.py
touch tests/ui.__init__.py
```

Then:
- Create `tests/ui/views.py`
- Create `tests/ui/urls.py` (This gets auto-discovered. Esnure some default home page rule.)

The templates for these tests, by contention, would be put in the app's templates directory as `templates/${APPNAME}/tests/ui`.

## Email testing

There are some helper base classes to test viewing email formatting and sending emails.
``` shell
hi.tests.ui.email_test_views.py
```
This requires the email templates follow the naming patterns expected in view classes.

