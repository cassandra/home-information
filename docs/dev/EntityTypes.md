<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Entity Types

## Adding New Entity Types

Add an new entry in this Enum:

``` shell
hi.apps.entity.enums.EntityType
```

Add the new type to the appropriate group in this Enum:

``` shell
hi.apps.entity.enums.EntityGroupType
```

Next, follow the section below depending on whether this is to be displayed as a icon, or as a path.

### Adding as an Icon

Create an SVG icon for the new entity type. However, this will only be the drawing commands for the SVG and should **not** include any wrapping `<svg>` element or other decorations.  See current examples for a clearer view. 

By default, the SVG viewbox for the icon will be `0 0 64 64`, but you can use a custom viewbox if needed (see below).  Put the SVG drawing commands in a file in the following directory and with the shown naming convention:

``` shell
hi/apps/entity/templates/entity/svg/type.${TYPE}.svg
```

The `${TYPE}` must match the enum's name, but with all lower case characters.

You should also add as the first drawing element a rectangle that covers the entire SVG viewbox.  This should not have any stroke or fill, but it ensures that the entire icon area is "clickable". Without this, clicks on transparent areas of the icon will have no effect. e.g.,

``` shell
<rect class="hi-entity-bg" x="0" y="0" width="64" height="64" fill="none"/>
```

If the SVG viewbox needed is not the default `0 0 64 64`, then also add an entry to the following dictionary to define the viewbox:

``` shell
hi.hi_styles.EntityStyle.EntityTypeToIconViewbox
```

Finally, add an entry to this set:
``` shell
hi.hi_styles.EntityStyle.EntityTypesWithIcons
```

### Adding as a Path

If the new entity type will be a closed path, then add to this set:

``` shell
hi.hi_styles.EntityStyle.EntityTypeClosedPaths
```

Else, if a closed path, add to the set:

``` shell
hi.hi_styles.EntityStyle.EntityTypeOpenPaths
```

Define which style to use for drawing the path. Usually, a new entity type requires defining a new style, but an existing style can be reused.  You reference the style to use for the new type in this dictionary:

``` shell
hi.hi_styles.EntityStyle.PathEntityTypeToSvgStatusStyle
```

When you need a new style for it, also add a new class variable to `hi.hi_styles.EntityStyle` with the type `SvgStatusStyle`. See the existing definitions for more details.

A closed path will default to appearing as a square, but you can adjust the default sizing by added an entry to this dictionary:

``` shell
hi.hi_styles.EntityStyle.EntityTypePathInitialRadius
```



### Simulator

If the new type is something you want the simulator to support (rare), then you will also need to add it there:

``` shell
hi.simulator.enums.SimEntityType
```
