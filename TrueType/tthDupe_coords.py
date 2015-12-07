#FLM: TT Hints Duplicator_coords
# coding: utf-8

__copyright__ = __license__ =  """
Copyright (c) 2015 Adobe Systems Incorporated. All rights reserved.

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""

__doc__ = u'''
TT Hints Duplicator_coords

This script was written to duplicate TT hinting data across compatible styles
of a typeface family, cutting the time needed for TT hinting by a significant
amount. The script is run as a FontLab macro, and does not need any of the
involved fonts to be open.

The script duplicates `tthints` files by reading information from the source
`tthints` file and associated fonts, and comparing this data to the target
fonts. It will not modify source- or target fonts in any way.

The script is smart enough to not re-process the source folder, so it is safe
to pick the root of a font project as the target directory.

This script imports the `TT Hints Duplicator` script, therefore needs to be
run from the same folder.

Note:
1)
This script will not process Delta hints. If Delta hints are present in a
glyph, an error message will be output, and the Delta hints omitted from the
output `tthints` file.

2)
The script can only process TT instructions that are attached to *on-curve*
points, because those are the only ones that will have the same coordinates
in both PS and TT outlines. If there are hints attached to off-curve points,
the whole glyph will be omitted from the output `tthints` file.

3)
It is expected that overlaps are removed in the source CFF and TTF files.
This ensures outline predictability.
Depending on the drawing it can mean that there is some work to be done for
compatibilizing the outlines across the style, which is usually less work
than re-hinting.

4)
Duplicating horizontal sidebearing-hints is not supported at this time.


==================================================
Versions:

v1.0 - Apr 18 2015 - First public release.
'''

import os
import sys

def findFile(fileName, path):
    'Find file of given fileName, starting at path.'
    for root, dirs, files in os.walk(path):
        if fileName in files:
            return os.path.join(root)
    else:
        return None

moduleName = 'tthDupe.py'
customModulePathMAC = os.path.join('~', 'Library', 'Application Support', 'FontLab', 'Studio 5', 'Macros')
customModulePathPC = os.path.join('~', 'Documents', 'FontLab', 'Studio5', 'Macros')
customModulePathMAC = os.path.expanduser(customModulePathMAC)
customModulePathPC = os.path.expanduser(customModulePathPC)
possibleModulePaths = [fl.userpath, customModulePathMAC, customModulePathPC]

print '\nLooking for %s ... ' % (moduleName)
for path in possibleModulePaths:
    modPath = findFile(moduleName, path)
    if modPath:
        print 'found at %s' % modPath
        break

if not modPath:
    # Module was not found. World ends.
    print 'Not found in the following folders:\n%s\n\
Please make sure the possibleModulePaths list in this script \
points to a folder containing %s' % ('\n'.join(possibleModulePaths), moduleName)

else:
    # Module was found, import it and run it.
    if not modPath in sys.path:
        sys.path.append(modPath)

    import tthDupe
    tthDupe.run(writeCoordinates=True)
