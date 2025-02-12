<img src="../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

_WORK IN PROGRESS_

# Design

## Branding, Icons, Logos



*** Gimp


*** ImageMagick
# Use this to scale images

sudo apt install imagemagick potrace
** MacOS setup
*** Python 3.11
# get python 3.11 package and install on OS X
https://www.python.org/downloads/
*** ImageMagick
# Use this to scale images

brew install imagemagick potrace


## Location SVGs

For best result use SVG viewbox at least 1200 in each direction and less than 2200.

Does not have to be square.

Create a series of individual SVG files with a single <path> tag to represent different types of features.  The <path> "id" attribute should have one of the following ids to indicate which feature it is:

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

If using Gimp, this translates to having a "Path" with the given name, then using the "Export Path" function since Gimp will add the path name as the path id.

With the individual SVG files assembled in a directory, run the following command to combine and format them into a single SVG suitable for importing.

./tools/combine-svgs.py -i <INPUT_DIR> -o <OUTPUT_FILE>

e.g., 

./tools/combine-svgs.py -i locations/bordeaux/paths -o locations/bordeaux/bordeaux.svg
./tools/combine-svgs.py -i locations/bordeaux-attic/paths -o locations/bordeaux-attic//bordeaux-attic.svg
./tools/combine-svgs.py -i locations/default/paths -o locations/default/default.svg

Try to keep the SVG image size on the small side. It will get loaded and manipulated by javascript, so past a certain size there will probably be issues.
