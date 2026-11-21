# Device Capabilities

Home Information runs on devices that may lack things a normal desktop browser has: a keyboard, browser navigation (back button, tabs, address bar) or user files to choose from and save to. A wall-mounted touch display in a kiosk browser typically lacks all three. A device declares what it lacks through capability flags; the user-facing side is in [Kiosk Setup](../../KioskSetup.md).

Flags describe the device (`keyboard`, `browser_nav`, `local_files`), never a kind of deployment. There is no "kiosk" or "touch" mode to branch on: an iPad is touch but has a keyboard and tabs, and one kiosk differs from another.

## Design Rule

New features must keep working on a device that lacks any of these capabilities:

1. **In-app content never opens a new tab or window.** Use in-app presentation instead, such as the full-screen file viewer (`templates/panes/file_viewer.html`). Only links that genuinely leave the app open a new tab, and those declare it (rule 4).
2. **Every full page has an in-app way home, and async failures never leave a frozen or blank screen.** Full-page error pages extend `templates/pages/error_base.html`, which has a HOME link. A lost session shows the Sign-in Required banner rather than failing silently.
3. **Viewing and controlling never require typing.** Prefer fixed choices (dropdowns, toggles, keypads) over free text where the set of values allows it. Typing is acceptable for adding and editing information, through rule 5.
4. **Message, don't hide.** A feature that needs a capability the device lacks stays visible. It declares the need, and the app explains why it is unavailable when the user tries it ("Not Available on This Device"). Don't hide features based on capabilities.
5. **Text entry on a keyboardless device goes through the app's on-screen keyboard** where the field supports it, and is otherwise blocked with the explanation from rule 4.

## Declaring Requirements

In templates (`{% load device_tags %}`, see `hi/apps/console/templatetags/device_tags.py`):

- `{% device_requires_attrs 'local_files' %}` on an element whose action needs a capability. Several names are allowed: `{% device_requires_attrs 'keyboard' 'local_files' %}`.
- `{% external_link_attrs %}` on every link that leaves the app. It opens a new tab and declares `browser_nav`.
- `handlers='on-screen-keyboard'` names an in-app handler that can stand in for a missing capability: `{% device_requires_attrs 'keyboard' handlers='on-screen-keyboard' %}`. Declare handler-served requirements on the field itself, not on a container: the handler only acts on an element that declares both.
- `{% device_capability_available 'keyboard' as device_has_keyboard %}` is for loading assets or choosing markup that depends on the device (e.g. the on-screen keyboard's script), not for hiding features (rule 4).

Unknown capability or handler names fail the render, since a misspelled declaration would otherwise gate nothing.

Text-entry controls (`textarea` and `input` types that can only be typed: text, email, password, search, url, tel) require the keyboard by default when they declare nothing themselves, unless disabled or read-only. A control's own declaration replaces the default, e.g. to name the on-screen keyboard handler.

## How It Works

- **Server:** `hi/apps/console/device_capabilities.py` holds the capabilities of the requesting device (`request.device_capabilities`) and the codec that maps them to their external names, used in query parameters, the cookie, markup and JavaScript. `/console/device` (`DeviceCapabilitiesView`) declares flags from query parameters and stores them in a long-lived cookie. `DeviceCapability` in `hi/apps/console/enums.py` holds each capability's user-facing reason.
- **Markup:** `hi/apps/console/device_markup.py` renders the `data-requires` and `data-requires-handler` attributes.
- **Client:** `src/hi/static/js/device.js` (`Hi.device`) blocks actions with unmet requirements in capture-phase listeners and asks the server for the explanation modal (`DeviceCapabilityUnavailableView`, rendered server-side). Handlers such as `onscreen-keyboard.js` register themselves when loaded. Code that acts on a field programmatically (e.g. focusing it), which the click gate never sees, should check `Hi.device.getUnmetRequirementsFor( element )` first.

**Known limit:** a browser's own long-press "open in new tab" menu can't be intercepted reliably.

### Adding a Capability

Add it to `DeviceCapability` (with its user-facing reason) and to the codec's name table in `DeviceCapabilitiesCodec`. All conversions between the enum and external names go through those explicit tables.

## Testing

- Python: `hi/apps/console/tests/` (`test_device_capabilities.py`, `test_device_markup.py`, `test_device_capability_unavailable_view.py`).
- JavaScript (QUnit): `src/hi/static/tests/test-device.js`, `test-onscreen-keyboard.js`, `test-keypad-entry.js`.

To try a feature as a keyboardless kiosk would, open `/console/device?keyboard=none&browser_nav=none&local_files=none` in your browser, and `/console/device?keyboard=default&browser_nav=default&local_files=default` to go back.
