#FLM: Input TrueType Hints_coords
# -*- coding: utf-8 -*-

import os
import sys

def findFile(fileName, path):
    'Find file of given fileName, starting at path.'
    for root, dirs, files in os.walk(path):
        if fileName in files:
            return os.path.join(root)
    else:
        return None

moduleName = 'InputTrueTypeHints.py'
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

    import InputTrueTypeHints
    InputTrueTypeHints.preRun(coord_option=True)
