#FontLab scripts for TrueType

These scripts all are tailored to a TrueType hinting workflow that invoves 
FontLab. Successfully tested in the following versions of FL:

- FontLab 5.1.2 Build 4447 (Mac)
- FontLab 5.1.5 Build 5714 (Mac)
- FontLab 5.2.1 Build 4868 (Win)

Dependencies (for `tthDupe.py`):

- Robofab
- FontTools (`ttx`)

## IMPORTANT
Mac users running OS 10.10 _Yosemite_ will run into several problems 
when trying to run those scripts from FontLab as they are used to. 

At the time of writing (April 2015), there is a bug in OSX Yosemite, which 
makes executing external code from FontLab difficult or even impossible. 
Since some of these scripts call the external `tx`, `ttx` and `type1` commands, 
this is a problem.  

In-depth description of this issue:  
http://forum.fontlab.com/index.php?topic=9134.0

An easy workaround is launching FontLab from the command line, like this:

    open "/Applications/FontLab Studio 5.app"

**This issue seems to have been fixed in Mac OS 10.11 _El Capitan_**


## Workflow

This workflow relies on the Adobe style for building fonts, which means using
a tree of folders, with one folder per style.


#### Step 1
The source files are UFOs. 
A `GlyphOrderAndAliasDB` file has been created in the root folder, which 
is a text file with (in most cases) two tab-separated columns. Those columns 
contain final glyph name and production glyph name for each glyph in the font. 

    Roman
        ├─ GlyphOrderAndAliasDB
        │
        ├─ Light
        │   └─ font.ufo
        │
        ├─ Regular
        │   └─ font.ufo
        │
        └─ Bold
            └─ font.ufo


#### Step 2
Run `convertToTTF.py` in Regular folder to get a VFB with TT outlines and a 
`font.ttf` file.

    Regular
        ├─ font.ttf
        ├─ font.ufo
        └─ font.vfb


#### Step 3
Hint the VFB file in FontLab, export the hints via `outputTTHints.py`, and 
export ppms via `outputPPMs.py`. This creates two new files, for storing 
this data externally. 

    Regular
        ├─ font.ttf
        ├─ font.ufo
        ├─ font.vfb
        ├─ ppms
        └─ tthints


#### Step 4
If you don’t trust this script, this is a good time to create a backup copy of 
your hinted VFB. 

Then, run `convertToTTF.py` again; this time pick the root folder of your 
font project. This will result in new `font.vfb` and `font.ttf` files for 
each folder. If the conversion script finds `tthints` and `ppms` files in 
any of the folders, they are applied to the newly-generated VFB and TTF.

    Roman
        ├─ GlyphOrderAndAliasDB
        │
        ├─ Light
        │   ├─ font.ttf
        │   ├─ font.ufo
        │   └─ font.vfb
        │
        ├─ Regular
        │   ├─ font.ttf
        │   ├─ font.ufo
        │   ├─ font.vfb
        │   ├─ MyFont_backup.vfb
        │   ├─ ppms
        │   └─ tthints
        │
        └─ Bold
            ├─ font.ttf
            ├─ font.ufo
            └─ font.vfb


#### Step 5
If outlines are compatible across weights, you can duplicate the TrueType hints 
with `tthDupe.py`. Note: outline compatibility must be given **with overlaps 
removed!** Run the script from FontLab, and first pick your template folder 
(in this case _Regular_), and then the root folder (in this case _Roman_).

The script creates new tthints files in each of the non-template folders: 

    Roman
        ├─ GlyphOrderAndAliasDB
        │
        ├─ Light
        │   ├─ font.ttf
        │   ├─ font.ufo
        │   ├─ font.vfb
        │   └─ tthints
        │
        ├─ Regular
        │   ├─ font.ttf
        │   ├─ font.ufo
        │   ├─ font.vfb
        │   ├─ MyFont_backup.vfb
        │   ├─ ppms
        │   └─ tthints
        │
        └─ Bold
            ├─ font.ttf
            ├─ font.ufo
            ├─ font.vfb
            └─ tthints


#### Step 6
Those new `tthints` files can be applied to new VFBs, again by running 
`convertToTTF.py`. It is likely that some errors happen during the conversion, 
so it is recommeded to check the new VFBs and improve the tthints files for each 
style. The script `outputTTHints.py` helps with that, it will modify but not 
overwrite extend the existing `tthints` file. 
It is also recommended to check, adjust and export `ppms` for each style.


#### Step 7
When all `tthints` and `ppms` are perfect, we can create final `font.ttf` files 
for the whole project with `convertToTTF.py`. Then, those `font.ttf` are used to 
build the final, manually hinted TT fonts:

    makeotf -f font.ttf

----

##### Background Info:

When PS outlines are converted to TT outlines, the number of points for a given
glyph is not always the same for all instances (even when generated from the
same, compatible masters). TT curve segments can be described with almost any 
number of off-curve points. As a result, the `tthints` files created for
one instance cannot simply  b reused as they are with any another instance,
even though the structure is similar. 
What `tthDupe.py` does is taking a note of the (on-curve) points TT instructions
are attached to, to correlate them with the points in the original PS font. 
This information can be used for finding new point indexes in a related TrueType 
instance.


See the Robothon 2012 talk on this problem here:  
[PDF slides with comments](http://typekit.files.wordpress.com/2012/04/truetype_hinting_robothon_2012.pdf) or [Video](http://vimeo.com/38352194)

See the Robothon 2015 talk explaining the TT workflow here:  
[Video](https://vimeo.com/album/3329572/video/123813230)


## Scripts

### `convertToTTF.py`
_FontLab menu name: **Convert PFA/UFO/TXT to TTF/VFB**_  
Reads an UFO, PFA, or TXT font file and outputs both a raw `font.ttf`  file and 
a `font.vfb` file. Those files may contain TT hints, which come from a 
conversion of PS hints. Therefore, it is recommended to `autohint` the input 
file before starting the TT conversion.  
If the script finds any `tthints` and `ppms` files the folder of the source file, 
this information is read and applied to output files.

### `inputTTHints.py`
_FontLab menu name: **Input TrueType Hints**_  
Reads an applies the contents of a `tthints` file to an open VFB.  
It is indifferent if this file references hints by point indexes or 
point coordinates.


### `outputPPMs.py`
_FontLab menu name: **Output PPMs**_  
Output PPMs (stem pixel jumps) as a simple `ppms` text file.


### `outputTTHints.py`
_FontLab menu name: **Output TrueType Hints**_  
Reads TT hints for selected glyphs and writes them to a simple `tthints` text
file. The script will read all possible hinting instructions in both directions,
and export all hints, also the hints attached to off-curve points. The idea is 
duplicating all FL hinting data in an external backup file.

If the external file already exists, the script will replace existing 
entries in that file, and/or add new ones. The script will emit an error 
message if hints are attached to off-curve points, but still write them. 


### `outputTTHints_coords.py`
_FontLab menu name: **Output TrueType Hints\_coords**_  
Like `outputTTHints.py`, but instead of point indexes, point coordinates are 
written. This script can be useful in the case that a TTF-VFB file has been 
created without the `convertToTTF.py` script (for instance directly from 
FontLab).
Since `convertToTTF.py` makes some outline corrections (e.g. fixing double 
points, which FontLab will write) the resulting TT outlines might not 
perfectly match the FontLab exported TT-outlines, and therefore point indexes
won’t match.  
Basically, the coordinate option is an attempt to save any hinting work that 
already has been done before using this workflow. 
The output data is written to a `tthints` file. 

This script imports `outputTTHints.py` as a module and therefore needs to be in 
the same folder.


### `tthDupe.py`
_FontLab menu name: **TT Hints Duplicator**_  
Macro to duplicate `tthints` files across compatible styles. The script was
created with the idea of re-using existing hinting patterns across different
weights, cutting the time investment for TT hinting by a significant amount.
The script is to be run from within FontLab, and does not need any of the
involved fonts to be open.  


### `tthDupe_coords.py`
_FontLab menu name: **TT Hints Duplicator\_coords**_  
Like `tthDupe.py`, but instead of point indexes, point coordinates are written. 

This script imports `tthDupe.py` as a module and therefore needs to be in 
the same folder.


__Important__: 

1. `tthDupe.py` can only process TT instructions that are attached to *on-curve* 
points, because those are the only ones that will have the same coordinates
in both PS and TT outlines. Source glyphs that have instructions attached to 
off-curve points will be dropped from the resulting `tthints` files.

2. The script will not duplicate Delta hints (by design), because Deltas are 
size- and style specific. They will simply be left out of the resulting 
`tthints` files. All the remaining hints of the glyph at hand will be written. 

3. It is expected that overlaps are removed in the source files. This ensures 
outline predictability. Depending on the drawing, this can mean some work for 
compatibilizing all outlines, which is usually less work than hinting.

4. Hinting of sidebearings is currently not supported in the duplicator script.

5. Hinting of components is also currently not supported. While this is 
possible in theory, many FL crashes prevent proper testing and proper 
implementation of this desirable feature.

