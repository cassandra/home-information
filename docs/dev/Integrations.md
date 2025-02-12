<img src="../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

_WORK IN PROGRESS_

# Integrations

- Each integration is a Django app in the `hi/services` directory.
- The `hi.integration` app handles integration management and required interfaces.

## Nomenclature

- **integration_id** - Unique identifier for each integration type
- **integration_key** - Used to associate with external integration for entities, sensors, controllers. etc
- **integration_attr_key** - Unique identifier for the user-defined attributes needed by the implementation

## How to Add an Integration

_Looking at an existing integration is the best way to see the pattern of what is needed._

Create a new Django app. e.g.,
``` shell
cd src/hi/services
../../manage.py startapp myintegration
cd ..
```

Ensure `name` is fully qualified in (e.g., `hi.services.myintegration`):
``` shell
hi/services/myintegration/app.py
```

Add 'myintegration' to `INSTALLED_APPS` in:
``` shell
hi/settings/base.py
```

Need this to be able to reference templates, e.g., `myintegration/panes/somepage.html`

Add to the IntegrationType enum

``` shell
    MYINTEGRATION    = ( 'My Integration', 'For my stuff.' )
```

Create subclass of enum `IntegrationAttributeType`. This defines the necessary attributes the integration needs (URLs, credentials, etc.)

Create an "Integration Gateway" using `IntegrationGateway`.
``` shell
hi/services/myintegration/myintegration_gateway.py
```

With content starting like this:

``` shell
from hi.integration.integration_gateway import IntegrationGateway

class MyIntegrationGateway( Singleton, IntegrationGateway ):
```

Add gateway to the `IntegrationFactory` class
``` shell
hi/integrations/integration_factory.py:get_integration_gateway()

from hi.services.myintegration.myintegration_gateway import MyIM

elif integration_type == IntegrationType.MYINTEGRATION:
  return MyIntegrationGateway

```

### Implement the IntegrationGateway Methods

#### Activate

In this simplest case, this can just update the status of the Integration DB object and display an 'info_message'.

In other caess, this allows an entry point into any activation flow. As a typical example, this would first render apage with a form for the user to fill out any prerequirsite integration properties. e.g., URLs, usernames, passwords, etc.

#### Deactivate

In this simplest case, this can just update the status of the Integration DB object and display an 'info_message'.

In other cases, this allows an entry point into a deact9ivation flow. For example, if the database entries associated with thei integration need to be removed, this could first gather and show all that need deletion and asking user for confirmation.

#### Manage

The manage method is the gateway to adding as much additional configuration views and administratuve features as needed.

Any additional views needed beside for enable, disable and manage should go through the 'manage' url with adding appropriate GET and POST parameters as needed for the particular admin feature.
``` shell
{% url 'integration_manage name=integration.integration_type.name %}
```
This url support both GET and POST, thoujgh bth go through the manage() method.
