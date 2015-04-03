#FLM: Input TrueType Hints_coords
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

__doc__ = """
Input TrueType Hints_coords

This FontLab macro will read an external simple text file `tthints_coords` 
containing TrueType instructions and hinted point coordinates for a number of
glyphs. The script and will apply that data to the glyphs of an open VFB.

Note:
This script imports the `Input TrueType Hints` script, therefore needs to be 
run from the same folder.

==================================================
Versions:

v1.0 - Mar 31 2015 - First public release.
"""

import os
import sys

def findFile(fileName, path):
    'Find file of given fileName, starting at path.'
    for root, dirs, files in os.walk(path):
        if fileName in files:
            return os.path.join(root)
    else:
        return None

moduleName = 'inputTTHints.py'
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

    import inputTTHints
    inputTTHints.preRun(coord_option=True)
