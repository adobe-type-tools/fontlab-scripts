#FLM: Output TrueType Hints_coords
# -*- coding: utf-8 -*-

import os
import sys

def findModulePath(moduleName, path):
    for root, dirs, files in os.walk(path):
        if moduleName in files:
            return os.path.join(root)
    else:
        return None

moduleName = 'OutputTrueTypeHints.py'
customModulePathMAC = os.path.join('~', 'Library', 'Application Support', 'FontLab', 'Studio 5', 'Macros')
customModulePathPC = os.path.join('~', 'Documents', 'FontLab', 'Studio5', 'Macros')

customModulePathMAC = os.path.expanduser(customModulePathMAC)
customModulePathPC = os.path.expanduser(customModulePathPC)
possibleModulePaths = [fl.userpath, customModulePathMAC, customModulePathPC]

print '\nLooking for %s ... ' % (moduleName)
for path in possibleModulePaths:
    modPath = findModulePath(moduleName, path)
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

    import OutputTrueTypeHints
    OutputTrueTypeHints.preRun(coord_option=True)
