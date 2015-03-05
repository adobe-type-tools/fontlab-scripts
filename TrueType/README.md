FontLab scripts for TrueType
====
### IMPORTANT:
Users running OS 10.10 _Yosemite_ will run into several problems when trying to 
just run those scripts from FontLab as they are used to. 

At the time of writing (March 2015), there is a bug in OSX Yosemite, which makes 
executing external code from FontLab difficult or even impossible. Since some of 
these scripts call the `tx` and `ttx` commands, this is a problem.  

In-depth description of this issue:  
http://forum.fontlab.com/index.php?topic=9134.0

An easy workaround is launching FontLab from the command line, like this:

    open "/Applications/FontLab Studio 5.app"

Then the scripts should work as expected. Hopefully this OSX bug will be fixed soon.

====

## `OutputTrueTypeHints.py`
_FontLab menu name: **Output TrueType Hints**_  
Writes a simple text file (`tthints`) which contains TrueType hinting 
instructions for each selected glyph. 
If the external file already exists, the script will replace 
existing entries and add new ones. The script will emit 
an error message if hints are attached to off-curve points.


## `InputTrueTypeHints.py`
_FontLab menu name: **Input TrueType Hints**_  
Reads an applies the contents of a `tthints` file to an open VFB.


## `ConvertToTTFandVFB.py`
_FontLab menu name: **Convert PFA/UFO/TXT to TTF/VFB**_  
Reads an UFO, PFA, or TXT font file and outputs both a raw `font.ttf` 
file and a `font.vfb` file. Those files may contain TT hints, 
which come from an automatic conversion of contained PS hints.  
Therefore, it is recommended to `autohint` the input file before 
starting the TTF work.

##### Workflow:
`ConvertToTTFandVFB.py` is called in two situations: 

- When the process of manual TT hinting starts, to create FontLab files to work with
- When the manual TT hinting is done, and `tthints` files have been 
exported. When re-run, the script will read and apply any adjacent `tthints` files 
to both the VFB and raw TTF file. After the hints have been applied the raw TTF file 
can be passed to `makeotf` to create a final TTF font.


## `tthDupe.py`
_FontLab menu name: **TT Hints Duplicator**_  
FL Macro to duplicate `tthints` files across compatible styles.
This script was created with re-using existing hinting patterns across 
different weights, cutting the time investment for TT hinting by a 
significant amount. The script is to be run from within FontLab, and 
does not need any of the involved fonts to be open.

##### Important: 

1. This script can only process anchors, single links, double links and 
interpolations in vertical direction. Support for further TT instructions 
could probably be added, but there was no need just yet.

2. The script can only process TT instructions that are attached to *on-curve* 
points, because those are the only ones that will have the same coordinates
in both PS and TT outlines.

3. It is expected that overlaps are removed in the source files. This
ensures outline predictability.
Depending on the drawing it can mean that there is some work to be done for 
compatibilizing the outlines, which is usually less work than hinting.



##### Workflow:

This workflow relies on the Adobe style for building fonts, which means using
a tree of folders, with one folder per style. In those folders, various files
are expected:

- one source file per folder, which has CFF (PS) outlines.        
  Multiple formats are possible: `font.ufo` or `font.pfa` or `font.txt`
  
- one file per folder with TTF outlines, created running `convertToTTFandVFB.py`,
  named `font.ttf`

- one template `tthints` file, which is created by hinting one style,
  and exporting the hints with e.g. `OutputTrueTypeHints.py`

- a `GlyphOrderAndAliasDB` file in the root folder, which mostly is a two-column 
  text file, and contains tab-separated columns for final name and production name.


An example tree could look like this – in this case, the source files are UFOs,
and the Regular VFB file has been hinted by hand. Then, a `tthints` file has been 
exported in the Regular folder:

    Roman
        ├─ GlyphOrderAndAliasDB
        │
        ├─ Light
        │   ├─ font.ttf
        │   └─ font.ufo
        │
        ├─ Regular
        │   ├─ font.ttf
        │   ├─ font.ufo
        │   ├─ font.vfb
        │   └─ tthints
        │
        └─ Bold
            ├─ font.ttf
            └─ font.ufo



Running this script on the Roman folder will generate `tthints` files for all the other styles 
within the same (compatible) family, which can then be applied via `InputTrueTypeHints.py`, 
or “sucked up” when processing with `convertToTTFandVFB.py`.



##### Background Info:

When PS outlines are converted to TT outlines, the number of points for a given
glyph is not always the same for all instances (even when generated from the
same, compatible masters), because curve segments can be described with almost any number 
of off-curve points. As a result, the `tthints` files created for one instance cannot simply 
be reused as they are with any another instance, even though the structure is similar.  
What this script does is taking a note of points which TT instructions are attached to, 
and correlate them with the points in the original PS font. This info can be used for 
finding new point indexes for any given on-curve point in a related TrueType instance.


See the Robothon 2012 talk on this problem here:  
[PDF slides with comments](http://typekit.files.wordpress.com/2012/04/truetype_hinting_robothon_2012.pdf) or [Video](http://vimeo.com/38352194)



##### Known Issues: 


`os.popen` is used to call `tx` and `ttx`.
It is true -- `os.popen` is deprecated; but any attempt to modernize this part
of the code just resulted in horrible crashes and (no kidding) kernel panics.

