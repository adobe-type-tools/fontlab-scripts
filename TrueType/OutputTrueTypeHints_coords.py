#FLM: Output TrueType Hints_coords
# -*- coding: utf-8 -*-

import os
import sys

def findModulePath(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root)

modPath = findModulePath('OutputTrueTypeHints.py', fl.usercommonpath)

if not modPath in sys.path:
    sys.path.append(modPath)

import OutputTrueTypeHints
OutputTrueTypeHints.preRun(coord_option=True)
