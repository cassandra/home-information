<img src="../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Getting Started

Once successfully running (see [Installation](Installation.md)), you should be greeted with the following starting page:

<img src="img/screenshot-start.png" alt="Home Information Start Page" width="400"> 

Click the "ADD MY LOCATION" button and then you should see this dialog:

<img src="img/screenshot-create.png" alt="Home Information Create Dialog" width="250"> 

All you need to provide is a name for your location to get started. 

The SVG file is optional and allows uploading a background image. The background can always be added later when you want to further customize the appearance.

If you did not upload your own SVG, then you should see the initial screen with the default background image like this:

<img src="img/screenshot-empty.png" alt="Home Information Initial Location View" width="400"> 

This view with the background graphic is called a "Location View".

## Editing Mode

You will start in "editing mode" where you can begin adding items to your home. When adding an item, it will appear in the middle of the screen, but you can move it around, change its size and change its orientation.

An an example, we'll add a refrigerator by clicking the "ADD NEW ITEM" button, giving it a name and choosing the "type" of item it is:

<img src="img/screenshot-add-item.png" alt="Home Information Add Item Dialog" width="250"> 

After clicking the add button, you will see an icon for the refrigerator in the middle of the screen.  We can now use the mouse or touch screen to reposition it. Click the icon to highlight it, then drag it to the position you want. Use the `s` key and thne the `+` and `-` keys to change its size.

<img src="img/screenshot-item-initial.png" alt="Home Information Initial Item" width="350">  <img src="img/screenshot-item-moved.png" alt="Home Information Moved Item" width="350"> 

There are many ways to adjust items, so see the "EDITING HELP" button on the bottom right of the screen for more information.

When selecting an item, the right side of the screen changes to show the details of that item. Although you can add attributes to the item in that area, editing mode is predominantly for adding and placing items.  Item attributes can be added any time, even when not in editing mode.  Clicking the "X" in the upper right of that area returns the side view to allow adding more items.

### Item Icons and Areas

The refrigerator type items will show with a refrigerator icon and many other types have their own icons.  However, some types of items can represent larger areas or allow you to define them with a custom shape. For example, let's show adding an "area" to represent a pool.  This pool item will allow us to keep all the information we have about our pool.

First click "ADD NEW ITEM", give it the name "Pool", choose the "Area" type and click the "ADD" button. 

<img src="img/screenshot-add-pool.png" alt="Home Information Adding Pool" width="350"> <img src="img/screenshot-pool-initial.png" alt="Home Information Initial Pool Item" width="350">

This will result in a square area that you can move and reshape. Click the square area to begin editing the shape. It will change color and show circles/dots where the lines meet. Click the dots to select then drag them to a new location until it has the shape you want.

<img src="img/screenshot-pool-selected.png" alt="Home Information Pool Selected" width="350"> <img src="img/screenshot-pool-moved.png" alt="Home Information Pool Moved" width="350">

You are not limited to square shapes either.  With an dot or line selected, press the `i` to insert new points and move them where you want.  Press the `ESC` key when done editing.

<img src="img/screenshot-pool-reshaped.png" alt="Home Information Pool Reshaped" width="350"> <img src="img/screenshot-pool-done.png" alt="Home Information Pool Done" width="350">

### Line Items

Another type of item is like an area, but for representing linear items. For example, suppose you have underground electric service and would like to show where the underground line runs. 

Click "ADD NEW ITEM", give it the name "Electric Service LIne", choose the "Electric Wire LIne" type and click the "ADD" button. 

<img src="img/screenshot-add-electric.png" alt="Home Information Adding Electric" width="350"> <img src="img/screenshot-electric-initial.png" alt="Home Information Initial Electric Item" width="350">

As with the area items, clicking it will give you the ability to edit by moving and/or adding points to it, pressing the `ESC` key when done.

<img src="img/screenshot-electric-selected.png" alt="Home Information Electric Selected" width="250"> <img src="img/screenshot-electric-moved.png" alt="Home Information Electric Moved" width="250"> <img src="img/screenshot-electric-done.png" alt="Home Information Electric Done" width="250">


### Collections

Not every item you may want to keep information about will make sense to have a specific location. For example, power tools and small appliances are items that you may have user manuals, replacement part info, etc.  Though you could add them as we have been, sometimes you just want to keep a list of these "movable" items.

A "collection" can be used to put items into meaningful groups, like "Small Appliances" or "Power Tools".  The bottom left of the screen will show all the defined collections, though we need to add some first by clicking the "ADD" button which brings up a dialog.

<img src="img/screenshot-add-collection.png" alt="Home Information Adding Collection" width="250"> 

A few notes about this dialog:
- The "Display" can be a List or Grid view, depending on your preferences.
- The "Order Id" just defines the order they will appear at the bottom of the screen.
- You can optionally represent the entire collection as one item in the graphical view if you want.

After adding, you will now see a button for the new collection at the bottom left. Clicking the button will change the main center view from the graphical location view to the collection view.  Here we could add existing items by clicking the checkboxes on the right panel.  Note that any items you add can appear in the graphical location view, the collection or both and you can easily toggle them on and off with a click of those checkboxes on the right.

<img src="img/screenshot-collection-initial.png" alt="Home Information Adding Collection" width="350">  <img src="img/screenshot-collection-empty.png" alt="Home Information Empty Collection" width="350"> 

However, since we have not added any small appliances yet, we can go and do this now by clicking the "ADD NEW ITEM" button.  When viewing a collection, that button adds a new item and will also add it to the collection.  When viewing the location view, it adds it to that view.  Here is what the collection view look like after adding a bunch of small appliances. It shows both the list view (left) and grid view (right).

<img src="img/screenshot-collection-list.png" alt="Home Information Collection List" width="350">  <img src="img/screenshot-collection-grid.png" alt="Home Information Collection Grid" width="350"> 

The message you see "_No status data available_" can be ignored for now. This refers to these items not being connected to any integations that monitor its status.  Integrations are discussed a little more below.

### Multiple Location Views

So far, we have seen just the one Location View.  As more and more items are added, a single screen can get cluttered, often with a mix of concerns that would be better separated.  We can add as many different Location Views as we need to do this.  Each Location View can define which items do an do not appear in the view and you can switch between views with the top left buttons.  An item can appear in just one or multiple views and/or multiple collections.

By default, you will see there is just one Location View created called "All".  In editing mode you will also see the "ADD" button to create new views.  Let's suppose we want to have aview that just focuses on the items in the Kitchen area. Click the "ADD" button, given it a name in the dialog and then you will see a new button and a new, but empty Location View.

<img src="img/screenshot-add-view.png" alt="Home Information New Location View" width="350">

We can add any existing kitchen items from the list at right, with the refrigerator being the only applicable one (unless you want to show all the small appliances too.)  Let's toggle the refrigerator and add a bunch of our other kitchen items: oven, cooktop, microwave, etc. We move and scale then as we did with the refrigerator to get something like this:

<img src="img/screenshot-view-initial.png" alt="Home Information Initial Location View" width="350">

This is a good start, but we'd also like to zoom in to focus just on that kitchen area.  The Location View allows zooming in and moving it around by clicking the background then using the mouse wheel, two finger pinching and/or dragging.  By doing this, you can show only the kitchen area.

<img src="img/screenshot-view-zoomed.png" alt="Home Information Zoomed Location View" width="350">

However, most of the time, zooming and moving the Location View is done on a temporary basis as you move around the view.  For the Kitchen view, we want to have this change permanent, so we need to enter the Location View editing pane in order for changes ot be saved.

Near the top right, there is the "View: Kitchen" label and a "EDIT" button to its right.  That is how to enter the editing mode for this location view to make any zooming and moving permanent. 

<img src="img/screenshot-view-edit.png" alt="Home Information Location View Edit" width="350">

 After adjusting view with the Location View editing area open, now when you click the "Kitchen" button on the top left, it will zoom in to that saved geometry.

### Multiple Locations

The Location Views we've seen so far are all defined with respect to a single "Location", which is the default location you gave a name to when your first started.  A single Location only has one background image and the Location Views are just different windows into that Location's image.

However, if you have a two-story house, an attic or basement, you may want to define two or three locations, so you can place items in a more logical place.  For example, if your Air Conditioner's Air Handler is in your attic and you want to keep information about it, it would make sense to define an "Attic" location and represent it there instead of placing it on the floor below.

When in editing mode, there is a Location drop-down on the top right that allows you to add a new Location.  This opens the same dialog as when you first started and created the initial location.  You given it a name and an optional SVG background image and from then on can change to that location with the drop down.

<img src="img/screenshot-add-location.png" alt="Home Information New Location" width="250"> <img src="img/screenshot-location-dialog.png" alt="Home Information Location Dialog" width="250"> <img src="img/screenshot-location-menu.png" alt="Home Information Location Menu" width="250">

Below is the Attic location's view after using a custom SVG background and adding the A/C Air Handler, some control wire routes, exhaust fans and a skylight.

<img src="img/screenshot-location-attic.png" alt="Home Information Attic Location" width="350">

## Normal Usage

So far, we have only focused on editing mode. However, editing is something you would only do initially and every once in a while. Normal usage is seen by using the "EXIT EDIT" button on the top right.  This normal operating mode allows you to changes views, zoom, move and click on items to view and add information.

Normal operation looks and behaves mostly the same as editing mode, but there is no option to add new items or relocate them. Instead, navigating around and clicking an item will bring up a dialog with all your previously added information about the item.  Here is what the normal view and item information dialog looks like for the previously added Kitchen view and after clicking on the Cooktop item.

<img src="img/screenshot-view-normal.png" alt="Home Information Normal View" width="350"> <img src="img/screenshot-item-edit.png" alt="Home Information Item Edit" width="350">

We have not yet added any attributes to the cooktop yet, but can do so now with the "Add New Attribute" button.  Add a name for the attribute and put in the information. For example, the make and model number might be information you want to keep.  You can also upload files, so it is a good place to keep a manual, purchase receipt, warranty information, repair information, etc.

Here is a sequence of adding purchase information and uploading a PDF of the item's specs.

<img src="img/screenshot-item-attribute.png" alt="Home Information Item Attribute" width="350"> <img src="img/screenshot-item-upload.png" alt="Home Information Item Upload" width="350">


## Other Features

### Weather Data

The weather data requires knowing your longitude and latitude.  These are located in the "Setting" page.  By default, these are set to Austin, TX, USA. The data comes from a few free weather APIs (e.g., National Weather Service, OpenMeteo).

### Location Attributes

All the items you add can have any number of attributes.  However, there are some attributes that may not belong to any item, but are are associated with the entire location.  For example, I have the elevation, GPS coordinates and Plat Map of the property for my home that I want to associated with the entire house Location itself.

For those higher-level, attributes, you can add them to a location using the "Info" button at top right just under the location drop down. That brings up a dialog where you can add location-specific attributes.

<img src="img/screenshot-location-edit.png" alt="Home Information Location Attribute" width="350"> 

### Bottom Right Buttons

#### Sounds

For features that use sounds (e.g., alerts), this allows toggling to mute and unmute.

#### Sleep

For always on devices, this darkens the screen in case the light is disruptive, but without stopping it from running. Just touch screen to brighten again.

#### Lock

When visitors are in your house, be they friends, acquaintences, service or maintenance people, you may want to temporarily lock the screen so they cannot access the information you've stored. To unlock, it uses a password you set the first time you lock the screen.

## Security States, Events, Alerts and Integations

Storing and accessing information about your home as shown above is useful, but it is only half of what Home Information was designed for.  With home security and home automation systems having become prevalent, these are now very important parts of the overall "Home Information" need.  With Google Home, Apple Home, Amazon Alex, etc.,  there is no shortage of platforms for managing those devices.  These platforms are device-centric and miss the information-centric view needed to truly unify all your home information in one place.

The Home Information app does not aim to build yet another device platform, but aims to build a unified interface into all your information.  To achieve that, it integrates with devices and platforms to pull in the data and controls needed for managing devices from a "single plane of glass" (as they say).

Many of the unmentioned buttons and features you see in the Home Information interface are for these integrations.  Integrations allow getting status information from devices and the ability to control those devices (using APIs).  With these integrations, you can then create security and automation views, define events and generate alerts for interesting events across all your devices and platforms.

We do not go any deeper into the integrations, events and alerts here as this page's intent is to just get you started with the basics.  See the [Integrations Page](Integrations.md) for more details.
