<img src="../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Custom Background Images

## Core Requirements

- Images must be in the SVG format.
- Must be well defined SVG structure.
- Recommended viewbox sizes in the 1500 to 3000 range.
- Any aspect ratio.

## Considerations

- Lighter, uncluttered images since all items get displayed over it.
- The fancier the SVG features you include, the less likely it has been tested in this app.

## Recommended Styling

If you use `<path>` drawing elements in the SVG, you can give then one of the pre-defined `class` atributes ot get some default styling.  e.g.,
```
<path class="grass" ...>
...
</path>
```

The predefined classes are:
```
asphalt
bathtubs
brick
ceiling-transitions
countertops
dead-space
door-arcs
doors
exterior-walls
fencing
fireplaces
floor-transitions
foliage
furniture
grass
gravel
ground
interior-floors
interior-walls
landscape-transitions
mulch
pavement
pavers
pool-coping
property-lines
rock-beds
secondary-walls
sheds
shelves
sinks
stairs
stone-walls
tiles
toilets
utilities
water
windows
wood-decks
```
