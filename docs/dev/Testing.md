<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Testing

## Unit Tests

``` shell
./manage.py test
```

## Integation Tests

_TBD_

## Visual Testing Page

Visit: [http://127.0.0.1:8411/tests/ui](http://127.0.0.1:8411/tests/ui).

These tests/ui views are only available in the development environment when `DEBUG=True`. (They are conditionally loaded in the root `urls.py`.)

### Adding to the Visual Testing Page

The `hi.tests.ui` module uses auto-discovery by looking in the app directories.

In the app directory you want to have a visual testing page:

``` shell
mkdir -p tests/ui
touch tests.__init__.py
touch tests/ui.__init__.py
```

Then:
- Create `tests/ui/views.py`
- Create `tests/ui/urls.py` (This gets auto-discovered. Esnure some default home page rule.)

The templates for these tests, by convention, would be put in the app templates directory as `templates/${APPNAME}/tests/ui`. At a minimum, you will probably want a home page `templates/${APPNAME}/tests/ui/home.html` like this:

``` html
{% extends "pages/base.html" %}
{% block head_title %}HI: PAGE TITLE{% endblock %}

{% block content %}
<div class="container-fluid m-4">

  <h2 class="text-info">SOME TESTS</h2>

  <!-- Put links to views here -->

</div>
{% endblock %}
```

And in `tests/ui/views.py`:

``` python
class Test${APPNAMNE}HomeView( View ):

    def get(self, request, *args, **kwargs):
        context = {
        }
        return render(request, "${APPNAME}/tests/ui/home.html", context )
```

And in `tests/ui/urls.py`:

``` python
from django.urls import re_path

from . import views


urlpatterns = [

    re_path( r'^$',
             views.TestUi${APPNAME}HomeView.as_view(), 
             name='${APPNAME}_tests_ui'),
]
```

### Email Testing

There are some helper base classes to test viewing email formatting and sending emails.
``` shell
hi.tests.ui.email_test_views.py
```
This requires the email templates follow the naming patterns expected in view classes.

