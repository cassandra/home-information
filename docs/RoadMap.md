<img src="../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# RoadMap

_High-level features only. Smaller task and refinements will just be part of the backlog ticketing process._

## Near Term

_In no particular order yet._

- **Weather Integrations** - Add weather integrations and show in default side panel.  Automatically adding weather alerts.
- **Auto-view Change** - When camera-related state changes fire, automatically show that camera's videop feed for a period of time before automatically reverting back to previous view.
- **Entity Cloning** - Allow an entity to be defined once, but have multiple visual reprpesentations on the screen.  Only one entity and attributes that is shared.
- **Internationalization** - Convert all display strings to use translatable structure (supported by Django). Also dealing with timezones and units.
- **Attribute Enhancements** - Introducing more specialized attributes and better UI elements for editing. e.g., Dates with a calendar, sliders, etc.
- **Virtual Whiteboard** - Allowing leaving messages through app like virtual "post-it note on the fridge".
- **Generic Camera Integration** - Add an integration that makes it easy to add any IP-based camera on the local network.
- **Path Editing in Aggregate** - Allow entire path to be moved, scaled, rotated at once instead of needing to relocate all the endpoints.
- **Better Test Automation** - Adding units tests, integration test and simulator-driven tests.

## Longer Term

_In no particular order yet._

- **First Time User Help** - Providing in-app and in-context help for first-time users. (Replacement for "Getting Started" guide.)
- **Location SVG Editor** - Allow users to more easily create their own custom background image.
- **Bar Code Scanning** - For automatically adding items and information about the items.
- **Mobile Device Uploads** - Streamline getting images from a phone into the app.
- **Measurement Annotations** - Allow the ability to add dimensional measurements for items who location wants to be captured more precisely.
- **Paths to use Bezier Curves** - Allow areas an dpath to use Bezier curves instead of always being linear segments.
- **Entity Archiving** - Ability to archive an entity that is no longer relevant without completely deleting it.
- **Data Export** - Ability to export all user data. JSON for entities an dattributes, zip file for uploaded documents.
- **Home and Personal Separation** - Ability to flag entities that are relaventr to the house versus more personal in nature, or not attached to the house per-se.  This leads to the notion that the house information can be transferred to a new owner without needing to transfer items that are not house related or which might be mopre personal in nature. Also leads to a permission system within the app based on the sensitivity and associations of the data/item.
- **Integation Security** - Better handling of any secrets needed for API credentials for APIs.
- **Search** - Ability to search across item names, attribute names, attribute values and uploaded documents.
- **Saas Offering** - Options are adding multi-tenant support or runing every user in an isolated single-tenant container. The latter is likely easier, and more secure.
