<img src="../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Kiosk Setup

A natural way to use Home Information is a dedicated screen that shows it all the time: a display on the kitchen wall, a tablet on a stand, or an old laptop on a shelf. It stays on, keeps the views up to date, and plays alert sounds when something needs attention, usually with nobody touching it. This page calls that a **kiosk**.

A kiosk is a deployment choice, not a requirement. Any browser works. What this page covers is what a kiosk needs to do its job well, and how to tell Home Information what the device can and can't do. How to build a kiosk (the hardware, the operating system, the browser setup) is outside the scope of Home Information, since there are many ways to do it.

## What a Kiosk Needs

Whatever device you use, check it against these:

- **Alert sounds play with nobody touching the screen.** This matters most, and it is where many devices fall short. Browsers treat alert sounds as "auto-play", and some only allow it after someone has touched the page. On iPads and iPhones this applies to every browser, since they all share Apple's browser engine: after a page reload, no sound plays until someone touches the screen. Home Information shows "Sounds: Blocked" when this happens. Tap it for help with your browser's settings.
- **The screen stays on.** The device must not sleep, lock itself or blank the screen. Dimming at night is fine (see [Dimming and Sleep Mode](#dimming-and-sleep-mode)).
- **It is readable from where you'll look at it.** Across the room usually means a larger screen than a typical tablet.
- **It recovers by itself.** If the browser crashes, or Home Information's server is down when the browser loads a page, the kiosk should get back to Home Information without anyone having to step in. Home Information keeps its own pages working through server outages and shows a message while the server is unreachable. But if the browser itself fails to load a page (for example, someone taps a link during an outage, or the browser restarts during one), the browser shows its own error page, and recovering from that is the kiosk's job, not Home Information's.
- **You can set the volume.** Tablets have volume buttons; wall displays often don't, and a monitor's own menus can be awkward. Set the device's sound output and its speakers to a level that carries across the room when you set the kiosk up.

## Choosing a Device

- **Tablets (iPad, Android).** Easy to set up, touch-friendly, with volume buttons and a keyboard that appears on screen. Check alert sounds carefully: on iPads the auto-play limit above means alerts can be silent after a reload until someone touches the screen. Browser controls (address bar, tabs) usually stay visible unless the device has a kiosk or single-app mode.
- **A computer with a touch display.** A small PC with a touch monitor can run a browser full-screen in a kiosk mode with auto-play allowed, so alert sounds always play. The trade-off is that such a setup usually has no keyboard, no browser controls and no useful files to choose from, which is what [Device Capabilities](#device-capabilities) is for. One example setup, for Ubuntu with Google Chrome, is [cassandra/kiosk](https://github.com/cassandra/kiosk). It isn't specific to Home Information.
- **A laptop.** An older laptop running a browser full-screen works the same way as a computer with a display, with its own keyboard and speakers.

## Device Capabilities

Home Information assumes a device has a keyboard, browser navigation (back button, tabs) and files to choose from or save to, as any normal browser does. A kiosk may lack some of these. Telling Home Information which ones are missing changes how it behaves on that device:

| Capability | When the device declares it missing (`none`) |
|---|---|
| `keyboard` | The sign-in email address is typed with an on-screen keyboard. Other features that need typing show a message instead of a text field you can't use. |
| `browser_nav` | Links that would leave Home Information (open another site or a new tab) show a message instead, since there would be no way back. |
| `local_files` | Adding files and other uploads or downloads show a message instead. |

Features that need a missing capability stay visible. When you tap one, a "Not Available on This Device" message explains why, rather than the feature silently not working or disappearing.

### Declaring Capabilities

Open this address once on the device, with the capabilities you want to declare:

```
http://<your-server>:<port>/console/device?keyboard=none&browser_nav=none&local_files=none
```

- Each capability takes one of three values: `none` (missing), `present` (available), or `default` (remove the declaration; same as never having declared it).
- Include only the capabilities you want to change. Others keep their current values.
- The page then goes to Home Information's main view, which shows the last view used on that device.
- This address works even when signed out or when the screen is locked, so you can set up a device before signing in.
- The declaration is stored in the browser on that device and lasts until you change it. It survives signing out, restarts and lost sessions. It does not apply to any other device.
- Capability names and values only work on this `/console/device` address; adding them to other addresses does nothing.

If the kiosk's browser opens a fixed start address every time it starts, use this address with your capabilities as that start address. The capabilities are then declared again on every restart, and the kiosk still returns to the last view.

### Examples

| Device | Address to open |
|---|---|
| Touch display with no keyboard, no browser controls, no file access | `/console/device?keyboard=none&browser_nav=none&local_files=none` |
| Laptop in a full-screen kiosk mode (has a keyboard, no browser controls) | `/console/device?keyboard=present&browser_nav=none&local_files=none` |
| Tablet or computer in a normal browser | Nothing to declare |
| Undo all declarations on a device | `/console/device?keyboard=default&browser_nav=default&local_files=default` |

## Using a Kiosk Without a Keyboard

- **Signing in:** type your email address with the on-screen keyboard, then enter the sign-in code from the email with the on-screen letter pad (the letter pad is used on every device).
- **Losing the session:** if the kiosk is signed out (for example, the server's sessions were reset), it shows a Sign-in Required banner rather than silently showing stale information.
- **Locking the screen:** the screen lock uses a 4-digit PIN entered on an on-screen keypad, on every device.
- **Viewing attached files:** files open in a full-screen viewer within Home Information, with a close button, rather than in a new browser tab.

## Dimming and Sleep Mode

A kiosk that is on all the time is often too bright at night. Two options, which work together:

- **Home Information's Sleep button** covers the screen with a very dark overlay. Everything keeps running, including alerts. Tap the screen to wake it. Sleep mode stays on through page reloads and browser restarts, as long as the kiosk's browser keeps its cookies (no private/incognito mode or profile that is erased on restart).
- **Scheduled dimming outside the browser.** Some kiosk setups lower the screen's actual brightness on a schedule, which also saves power and backlight life.

Avoid settings that turn the screen off or put the device to sleep: alerts would no longer be seen, and possibly not heard.
