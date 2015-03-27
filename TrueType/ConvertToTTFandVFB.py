#FLM: Convert PFA/UFO/TXT to TTF/VFB
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

This FontLab script will convert one or more hinted PFA/UFO or TXT files
into TTF files, for use as input for makeOTF.
The script will first ask for a directory, which usually should be the 
family's top-most folder. It will then crawl through that folder and 
process all input files it finds. In addition to the directory, the script 
will also ask for an encoding file. This encoding file is a FontLab '.enc'
file which the script will use for ordering the glyphs.

==================================================

Versions:

v1.2 - Mar 26 2015 - Move TT hint file reading code to adjacent module.
v1.1 - Mar 23 2015 - Allow instructions in x-direction.
v1.0 - Mar 04 2015 - Initial public release (Robothon 2015).

"""

import os
import re
import sys
import time

import InputTrueTypeHints
reload(InputTrueTypeHints)

from FL import *
import fl_cmd

try:
    import dvInput_module
    dvModuleFound = True
except:
    dvModuleFound = False


MAC = False
PC  = False
if sys.platform in ('mac', 'darwin'): MAC = True
elif os.name == 'nt': PC = True


# Adding the FDK Path to the env variable (on Mac only) so 
# that command line tools can be called from FontLab:'
if MAC:
    fdkPathMac = os.sep.join((os.path.expanduser('~'), 'bin', 'FDK', 'tools', 'osx'))
    envPath = os.environ["PATH"]
    newPathString = envPath + ":" + fdkPathMac
    if fdkPathMac not in envPath:
        os.environ["PATH"] = newPathString


# constants:
kNULLglyphName   = "NULL"
kCRglyphName     = "CR"
kPPMsFileName    = "ppms"
kTTHintsFileName = "tthints"
kGOADBfileName   = "GlyphOrderAndAliasDB"
kTempEncFileName = ".tempEncoding"

kFontTXT = "font.txt"
kFontUFO = "font.ufo"
kFontTTF = "font.ttf"

# find-replace text for patching the `prep` table with TTX
kPrepTableFind = """WCVTP[ ]\t/* WriteCVTInPixels */\n    </assembly>"""
kPrepTableReplace = """WCVTP[ ]\t/* WriteCVTInPixels */\n      MPPEM[ ]\n      PUSHW[ ]\t/* 1 value pushed */\n      96\n      GT[ ]\n      IF[ ]\n      PUSHB[ ]\t/* 1 value pushed */\n      1\n      ELSE[ ]\n      PUSHB[ ]\t/* 1 value pushed */\n      0\n      EIF[ ]\n      PUSHB[ ]\t/* 1 value pushed */\n      1\n      INSTCTRL[ ]\n    </assembly>"""

conversionOptions = []
convertT1toTTOptionsProcessed = False
changeTTfontSettingsProcessed = False
setType1openPrefsProcessed = False
setTTgeneratePrefsProcessed = False
setTTautohintPrefsProcessed = False

baselineZonesWereRemoved = False
fontZonesWereReplaced = False

hPPMsList = []
vPPMsList = []
stemsAndPPMsEdited = False

ttHintsList = []
ttHintsEdited = False

flPrefs = Options()
flPrefs.Load()


def getFontPaths(path):
    fontsList = []

    for root, folders, files in os.walk(path):
        fileAndFolderList = folders[:]
        fileAndFolderList.extend(files)

        pfaRE = re.compile(r'(^.+?\.pfa)$', re.IGNORECASE)
        ufoRE = re.compile(r'(^.+?\.ufo)$', re.IGNORECASE)
        txtRE = re.compile(r'^font.txt$', re.IGNORECASE)

        pfaFiles = [match.group(1) for item in fileAndFolderList for match in [pfaRE.match(item)] if match]
        ufoFiles = [match.group(1) for item in fileAndFolderList for match in [ufoRE.match(item)] if match]
        txtFiles = [match.group(0) for item in fileAndFolderList for match in [txtRE.match(item)] if match]

        # Prioritizing the list, so that only one source files is found and converted.
        # Order of priority is PFA - UFO - TXT:
        allFontsFound = pfaFiles + ufoFiles + txtFiles

        if len(allFontsFound):
            print allFontsFound
            item = allFontsFound[0]
            fontsList.append(os.path.join(root, item))

        else:
            continue

    return fontsList


def readFile(filePath):
    file = open(filePath, 'r')
    fileContent = file.read().splitlines()
    file.close()
    return fileContent


def writeFile(contentList, filePath):
    outfile = open(filePath, 'w')
    outfile.writelines(contentList)
    outfile.close()


# Get the second column of the original GOADB file and return it as a list
def getGOADB2ndColumn(goadbList):
    resultList = []
    lineNum = 1
    skippedLines = 0
    re_match1stCol = re.compile(r"(\S+)\t(\S+)(\t\S+)?")
    
    for line in goadbList:
        # Skip over blank lines
        line2 = line.strip()
        if not line2:
            skippedLines += 1
            continue

        result = re_match1stCol.match(line)
        if result: #the result can be None
            resultList.append(result.group(2) + '\n')
        else: #nothing matched
            print "Problem matching line %d (current GOADB)" % lineNum
        
        lineNum +=1

    if (len(goadbList) != (len(resultList) + skippedLines)):
        print "ERROR: There was a problem processing the current GOADB file"
        return None
    else:
        return resultList


def makeTempEncFileFromGOADB(goadbPath):
    goadbFileContent = readFile(goadbPath)

    goadb2ndColumnList = getGOADB2ndColumn(goadbFileContent)
    if not goadb2ndColumnList:
        return None
    
    encPath = os.path.join(os.path.dirname(goadbPath), kTempEncFileName)
    writeFile(goadb2ndColumnList, encPath)
    return encPath


def readPPMsFile(filePath):
    file = open(filePath, "r")
    data = file.read()
    file.close()
    lines = data.splitlines()

    # Empty PPM lists
    del hPPMsList[:]
    del vPPMsList[:]
    
    for i in range(len(lines)):
        line = lines[i]
        # Skip over blank lines
        line2 = line.strip()
        if not line2:
            continue
        # Get rid of all comments
        if line.find('#') >= 0:
            continue
        else:
            if "X:" in line:
                vPPMsList.append(line)
            else:
                hPPMsList.append(line)


def replaceStemsAndPPMs():
    global stemsAndPPMsEdited

    if len(hPPMsList) != len(fl.font.ttinfo.hstem_data):
        print "\tERROR: The amount of H stems does not match"
        return
    if len(vPPMsList) != len(fl.font.ttinfo.vstem_data):
        print "\tERROR: The amount of V stems does not match"
        return

    stemsAndPPMsEdited = True
    
    for i in range(len(fl.font.ttinfo.hstem_data)):
        name, width, ppm2, ppm3, ppm4, ppm5, ppm6 = hPPMsList[i].split('\t')
        stem = TTStem()
        stem.name = name
        stem.width = int(width)
        stem.ppm2 = int(ppm2)
        stem.ppm3 = int(ppm3)
        stem.ppm4 = int(ppm4)
        stem.ppm5 = int(ppm5)
        stem.ppm6 = int(ppm6)
        fl.font.ttinfo.hstem_data[i] = stem

    for i in range(len(fl.font.ttinfo.vstem_data)):
        name, width, ppm2, ppm3, ppm4, ppm5, ppm6 = vPPMsList[i].split('\t')
        stem = TTStem()
        stem.name = name
        stem.width = int(width)
        stem.ppm2 = int(ppm2)
        stem.ppm3 = int(ppm3)
        stem.ppm4 = int(ppm4)
        stem.ppm5 = int(ppm5)
        stem.ppm6 = int(ppm6)
        fl.font.ttinfo.vstem_data[i] = stem


def processZonesArray(inArray):
    outArray = []
    for x in range(len(inArray)/2):
        if inArray[x * 2] < 0:
            outArray.append(inArray[x * 2])
            outArray.append(inArray[x * 2 + 1])
    outArray.sort()
    return outArray


def removeBottomZonesAboveBaseline():
    global baselineZonesWereRemoved
    newOtherBluesArray = processZonesArray(fl.font.other_blues[0])  # this is a single master font, so only the first array will have non-zero values
    if (fl.font.other_blues_num != len(newOtherBluesArray)): baselineZonesWereRemoved = True
    fl.font.other_blues_num = len(newOtherBluesArray)  # trim the number of zones

    for x in range(len(newOtherBluesArray)):
        fl.font.other_blues[0][x] = newOtherBluesArray[x]
    
    newFamilyOtherBluesArray = processZonesArray(fl.font.family_other_blues[0])
    if (fl.font.family_other_blues_num != len(newFamilyOtherBluesArray)): baselineZonesWereRemoved = True
    fl.font.family_other_blues_num = len(newFamilyOtherBluesArray)
    
    for x in range(len(newFamilyOtherBluesArray)):
        fl.font.family_other_blues[0][x] = newFamilyOtherBluesArray[x]


def replaceFontZonesByFamilyZones():
    """The font's zones are replaced by the family zones to make sure that 
       all the styles have the same vertical height at all ppems.
       If the font doesn't have family zones (e.g. Regular style), don't do anything."""
    global fontZonesWereReplaced
    # TOP zones
    if len(fl.font.family_blues[0]):
        if fl.font.family_blues_num == 14 and fl.font.blue_values_num < fl.font.family_blues_num:
            print
            print "### MAJOR ERROR ###: Due to a FontLab bug the font's TOP zones cannot be replaced by the family TOP zones"
            print
            return
        elif fl.font.family_blues_num == 14 and fl.font.blue_values_num == fl.font.family_blues_num:
            pass
        else:
            fl.font.blue_values_num = fl.font.family_blues_num # This will create a traceback if there are 7 top zones, therefore the IFs above
        # Replace the font's zones by the family zones
        for x in range(len(fl.font.family_blues[0])):
            fl.font.blue_values[0][x] = fl.font.family_blues[0][x]
        print "WARNING: The font's TOP zones were replaced by the family TOP zones."
        fontZonesWereReplaced = True
    # BOTTOM zones
    if len(fl.font.family_other_blues[0]):
        if fl.font.family_other_blues_num == 10 and fl.font.other_blues_num < fl.font.family_other_blues_num:
            print
            print "### MAJOR ERROR ###: Due to a FontLab bug the font's BOTTOM zones cannot be replaced by the family BOTTOM zones"
            print
            return
        elif fl.font.family_other_blues_num == 10 and fl.font.other_blues_num == fl.font.family_other_blues_num:
            pass
        else:
            fl.font.other_blues_num = fl.font.family_other_blues_num # This will create a traceback if there are 5 bottom zones, therefore the IFs above
        # Replace the font's zones by the family zones
        for x in range(len(fl.font.family_other_blues[0])):
            fl.font.other_blues[0][x] = fl.font.family_other_blues[0][x]
        print "WARNING: The font's BOTTOM zones were replaced by the family BOTTOM zones."
        fontZonesWereReplaced = True


def convertT1toTT():
    global convertT1toTTOptionsProcessed
    
    for g in fl.font.glyphs:

        # Keeping track of original start point coordinates:
        startPointCoords = [(point.x, point.y) for point in g.nodes if point.type == 17]

        # fl.TransformGlyph(g, 5, "0001")  # Remove Horizontal Hints
        # fl.TransformGlyph(g, 5, "0003")  # Remove Horizontal & Vertical Hints
        fl.TransformGlyph(g, 5, "0002")  # Remove Vertical Hints
        fl.TransformGlyph(g, 13, "")     # Curves to TrueType
        fl.TransformGlyph(g, 14, "0001") # Contour direction [TT]
        fl.TransformGlyph(g, 7, "")      # Convert to instructions
        
        # The start points move when FL reverses the contour. Annoying!
        # This dictionary keeps track of the new coordinates.
        newCoordDict = {(node.x, node.y): index for index, node in enumerate(g.nodes)}
        
        # Going through all start points backwards, and re-setting them to original position.
        for pointCoords in startPointCoords[::-1]:
            g.SetStartNode(newCoordDict[pointCoords])

        if not convertT1toTTOptionsProcessed:
            conversionOptions.append("Bottom zones above baseline removed")
            conversionOptions.append("Type 1 vertical glyph hints removed")
            conversionOptions.append("Outlines converted to TrueType format")
            conversionOptions.append("Countour direction set to TrueType")
            conversionOptions.append("Hints converted to TrueType instructions")
            convertT1toTTOptionsProcessed = True


def changeTTfontSettings():
    global changeTTfontSettingsProcessed
    # Clear `gasp` array
    if len(fl.font.ttinfo.gasp):
        del fl.font.ttinfo.gasp[0]
    # Create `gasp` element
    gaspElement = TTGasp(65535, 2) 
    # Range: 65535=0... 
    # Options: 0=None 1=Instructions 2=Smoothing 3=Instructions+Smoothing
    
    # Add element to `gasp` array
    fl.font.ttinfo.gasp[0] = gaspElement
    
    # Clear `hdmx` array
    for i in range(len(fl.font.ttinfo.hdmx)):
        try:
            del fl.font.ttinfo.hdmx[0]
        except:
            continue
    
    # Uncheck "Create [vdmx] table", also
    # uncheck "Automatically add .null, CR and space characters"
    fl.font.ttinfo.head_flags = 0
    
    if not changeTTfontSettingsProcessed:
        if not len(fl.font.ttinfo.hdmx):
            hdmxArray = None
        else:
            hdmxArray = fl.font.ttinfo.hdmx
        conversionOptions.append("'gasp' table: %s" % fl.font.ttinfo.gasp[0])
        conversionOptions.append("'hdmx' table: %s" % hdmxArray)
        conversionOptions.append("'vdmx' table: %s" % fl.font.ttinfo.head_flags)
        changeTTfontSettingsProcessed = True


def setType1openPrefs():
    global setType1openPrefsProcessed
    flPrefs.T1Decompose     = 1 # checked   - Decompose all composite glyphs
    flPrefs.T1Unicode       = 0 # unchecked - Generate Unicode indexes for all glyphs
    flPrefs.OTGenerate      = 0 # unchecked - Generate basic OpenType features for Type 1 fonts with Standard encoding
    flPrefs.T1MatchEncoding = 0 # unchecked - Find matching encoding table if possible
    
    if not setType1openPrefsProcessed:
        conversionOptions.append("T1Decompose = %d" % flPrefs.T1Decompose)
        conversionOptions.append("T1Unicode = %d" % flPrefs.T1Unicode)
        conversionOptions.append("OTGenerate = %d" % flPrefs.OTGenerate)
        conversionOptions.append("T1MatchEncoding = %d" % flPrefs.T1MatchEncoding)
        setType1openPrefsProcessed = True


def setTTgeneratePrefs():
    global setTTgeneratePrefsProcessed
    flPrefs.TTENoReorder        = 1 # unchecked - Automatically reorder glyphs
    flPrefs.TTEFontNames        = 1 # option    - Do not export OpenType name records
    flPrefs.TTESmartMacNames    = 0 # unchecked - Use the OpenType names as menu names on Macintosh
    flPrefs.TTEStoreTables      = 0 # unchecked - Write stored custom TrueType/OpenType tables
    flPrefs.TTEExportOT         = 0 # unchecked - Export OpenType layout tables
    flPrefs.DSIG_Use            = 0 # unchecked - Generate digital signature (DSIG table)
    flPrefs.TTEHint             = 1 # checked   - Export hinted TrueType fonts
    flPrefs.TTEKeep             = 1 # checked   - Write stored TrueType native hinting
    flPrefs.TTEVisual           = 1 # checked   - Export visual TrueType hints
    flPrefs.TTEAutohint         = 0 # unchecked - Autohint unhinted glyphs
    flPrefs.TTEWriteBitmaps     = 0 # unchecked - Export embedded bitmaps
    flPrefs.CopyHDMXData        = 0 # unchecked - Copy HDMX data from base to composite glyph
    flPrefs.OTWriteMort         = 0 # unchecked - Export "mort" table if possible
    flPrefs.TTEVersionOS2       = 3 # option    - OS/2 table version 3
    flPrefs.TTEWriteKernTable   = 0 # unchecked - Export old-style non-OpenType "kern" table
    flPrefs.TTEWriteKernFeature = 0 # unchecked - Generate OpenType "kern" feature if it is undefined or outdated
    flPrefs.TTECmap10           = 1 # option    - Use following codepage to build cmap(1,0) table:
                                    #             [Current codepage in the Font Window]
    flPrefs.TTEExportUnicode    = 0 # checked   - Ignore Unicode indexes in the font
                                    # option    - Use following codepage for first 256 glyphs:
                                    #             Do not reencode first 256 glyphs
                                    # unchecked - Export only first 256 glyphs of the selected codepage
                                    # unchecked - Put MS Char Set value into fsSelection field

    if not setTTgeneratePrefsProcessed:
        conversionOptions.append("TTENoReorder = %d" % flPrefs.TTENoReorder)
        conversionOptions.append("TTEFontNames = %d" % flPrefs.TTEFontNames)
        conversionOptions.append("TTESmartMacNames = %d" % flPrefs.TTESmartMacNames)
        conversionOptions.append("TTEStoreTables = %d" % flPrefs.TTEStoreTables)
        conversionOptions.append("TTEExportOT = %d" % flPrefs.TTEExportOT)
        conversionOptions.append("DSIG_Use = %d" % flPrefs.DSIG_Use)
        conversionOptions.append("TTEHint = %d" % flPrefs.TTEHint)
        conversionOptions.append("TTEKeep = %d" % flPrefs.TTEKeep)
        conversionOptions.append("TTEVisual = %d" % flPrefs.TTEVisual)
        conversionOptions.append("TTEAutohint = %d" % flPrefs.TTEAutohint)
        conversionOptions.append("TTEWriteBitmaps = %d" % flPrefs.TTEWriteBitmaps)
        conversionOptions.append("CopyHDMXData = %d" % flPrefs.CopyHDMXData)
        conversionOptions.append("OTWriteMort = %d" % flPrefs.OTWriteMort)
        conversionOptions.append("TTEVersionOS2 = %d" % flPrefs.TTEVersionOS2)
        conversionOptions.append("TTEWriteKernTable = %d" % flPrefs.TTEWriteKernTable)
        conversionOptions.append("TTEWriteKernFeature = %d" % flPrefs.TTEWriteKernFeature)
        conversionOptions.append("TTECmap10 = %d" % flPrefs.TTECmap10)
        conversionOptions.append("TTEExportUnicode = %d" % flPrefs.TTEExportUnicode)
        setTTgeneratePrefsProcessed = True


def setTTautohintPrefs():
    global setTTautohintPrefsProcessed
    # The single link attachment precision is 7 in all cases
    # flPrefs.TTHHintingOptions = 16135 # All options checked
    # flPrefs.TTHHintingOptions = 7     # All options unchecked
    flPrefs.TTHHintingOptions = 2055  # Cusps option checked
    
    if not setTTautohintPrefsProcessed:
        conversionOptions.append("TTHHintingOptions = %d" % flPrefs.TTHHintingOptions)
        setTTautohintPrefsProcessed = True


def addNULLandCRglyphs():
    if fl.font.FindGlyph(kNULLglyphName) == -1:
        fl.font.glyphs.append(fl.font.GenerateGlyph("space=" + kNULLglyphName))
    if fl.font.FindGlyph(kCRglyphName) == -1:
        fl.font.glyphs.append(fl.font.GenerateGlyph("space=" + kCRglyphName))
    # Fix NULL advance width
    fl.font[kNULLglyphName].width = 0


def fixGlyphNames(ttFont):
    if MAC:
        ttxTool = "ttx"
    if PC:
        ttxTool = "ttx.cmd"

    command = "%s -t GlyphOrder -t post -t prep '%s'" % (ttxTool, ttFont)

    # Run TTX to get GlyphOrder, 'post' table and 'prep' table
    pp = os.popen(command)
    report = pp.read()
    pp.close()
    
    # Get TTX file name (on Windows, the file name is hard-coded)
    m = re.search(r"to\s+\"([^\"]+)\"", report) # ttx message: Dumping "font.ttf" to "font.ttx"...
    if not m:
        print "ERROR: Failed to extract source TTF font post table with 'ttx' tool. Report follows."
        print report
        return
    
    # Read content of ttx file
    ttxFont = m.group(1) # ttx file name
    
    # Open TTX file
    fp = open(ttxFont, "rt")
    ttxData = fp.read()
    fp.close()
    
    # Rename glyphs
    if ttxData.find('name="nonmarkingreturn"') != -1:
        ttxData = ttxData.replace('name="nonmarkingreturn"','name="CR"') # Replace glyph name in GlyphOrder table
        ttxData = ttxData.replace('</extraNames>','  <psName name="CR"/>\n    </extraNames>') # Add entry to post table
    
    if ttxData.find('name="nonbreakingspace"') != -1:
        ttxData = ttxData.replace('name="nonbreakingspace"','name="nbspace"')
        ttxData = ttxData.replace('</extraNames>','  <psName name="nbspace"/>\n    </extraNames>') # Add entry to post table

    # Find-replace data in TTX font to stop TT hints kicking in at 96 ppm and above.
    if ttxData.find(kPrepTableFind) != -1:
        print 'fixing `prep` table ...'
        ttxData = ttxData.replace(kPrepTableFind,kPrepTableReplace)
    # else:
    #     print '`prep` table string not found in ttx file.\nNo modifications to table made.'

    # Write modifications to TTX file
    fp = open(ttxFont, "wt")
    fp.write(ttxData)
    fp.close()

    command = "%s -m '%s' '%s'" % (ttxTool, ttFont, ttxFont)

    # Merge changes into TT font
    pp = os.popen(command)
    report = pp.read()
    pp.close()
    
    # Delete files
    # os.remove(ttFont) # This is the original TT font
    os.remove(ttxFont) # This is the temporary TTX file
    
    m = re.search(r"to\s+\"([^\"]+)\"", report) # ttx message: Compiling "font.ttx" to "font#1.ttf"...
    if not m:
        print "ERROR: Failed to merge changes into TTF font with 'ttx' tool. Report follows."
        print report
        return

    newTTFName = m.group(1) # file name of new TT file, usually 'font#1.ttf'
    if newTTFName != ttFont:
        os.rename(newTTFName, ttFont) # Renames the new file
    
    return 1


def convertTXTfontToPFA(txtPath):
    tempPFApath = txtPath.replace('.txt','_TEMP_.pfa')
    
    if MAC:
        type1Tool = "type1"
    if PC:
        type1Tool = "type1.exe"

    command = "%s '%s' > '%s'" % (type1Tool, txtPath, tempPFApath)
    
    # Run type1 tool
    if MAC:
        pp = os.popen(command)
        report = pp.read()
        pp.close()
    if PC:
        pp = Popen(command)
    
    return tempPFApath


def convertUFOfontToPFA(ufoPath):
    tempPFApath = ufoPath.replace('.ufo','_TEMP_.pfa')
    
    if MAC:
        txTool = "tx"
    if PC:
        txTool = "tx.cmd"

    command = "%s -t1 '%s' > '%s'" % (txTool, ufoPath, tempPFApath)
    
    # Run tx tool
    if MAC:
        pp = os.popen(command)
        report = pp.read()
        pp.close()
    if PC:
        pp = Popen(command)
    
    return tempPFApath


def processFonts(fontsList):
    totalFonts = len(fontsList)
    
    print "%d fonts found:\n%s\n" % (totalFonts, '\n'.join(fontsList))
    
    setType1openPrefs()
    setTTgeneratePrefs()
    setTTautohintPrefs()
    
    i = 1
    for pfaPath in fontsList:
        # Make temporary encoding file from GOADB file.
        # This step needs to be done per font, because the directory tree selected 
        # may contain more than one family, or because the glyph set of a given family
        # may not be the same for both Roman/Upright and Italic/Sloped.
        encPath = None
        goadbPath = None
    
        # The GOADB can be located in the same folder or up to two levels above in the directory tree
        sameLevel = os.path.join(os.path.dirname(pfaPath), kGOADBfileName)
        oneUp = os.path.join(os.path.dirname(os.path.dirname(pfaPath)), kGOADBfileName)
        twoUp = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(pfaPath))), kGOADBfileName)
    
        if os.path.exists(sameLevel):
            goadbPath = sameLevel
        elif os.path.exists(oneUp):
            goadbPath = oneUp
        elif os.path.exists(twoUp):
            goadbPath = twoUp
        
        if goadbPath:
            encPath = makeTempEncFileFromGOADB(goadbPath)
        else:
            print "Could not find %s file." % kGOADBfileName
            print "Skipping %s" % pfaPath
            print
    
        if not encPath:
            continue

        # checking if a derivedchars file exists; if not, the dvInput step is skipped.
        makeDV = False

        for file in os.listdir(os.path.split(pfaPath)[0]):
            if re.search(r'derivedchars(.+?)?$', file) and dvModuleFound:
                makeDV = True
                
        fontIsTXT = False
        fontIsUFO = False

        if kFontTXT in pfaPath:
            fontIsTXT = True
            pfaPath = convertTXTfontToPFA(pfaPath)

        elif kFontUFO in pfaPath or (pfaPath[-4:].lower() in [".ufo"]): # Support more than just files named "font.ufo"
            fontIsUFO = True
            pfaPath = convertUFOfontToPFA(pfaPath)
        
        fl.Open(pfaPath)
        print "Processing %s ... (%d/%d)" % (fl.font.font_name, i, totalFonts)
        i += 1
    
        replaceFontZonesByFamilyZones()
        removeBottomZonesAboveBaseline()
        
        # NOTE: After making changes to the PostScript alignment zones, the TrueType equivalents 
        # have to be updated as well, but I couldn't find a way to do it via scripting (because 
        # TTH.top_zones and TTH.bottom_zones are read-only, and despite that functionality being 
        # available in the UI, there's no native function to update TT zones from T1 zones).
        # So the solution is to generate a new T1 font and open it back.
        pfaPathTemp = pfaPath.replace('.pfa','_TEMP_.pfa')
        infPathTemp = pfaPathTemp.replace('.pfa','.inf')
        if baselineZonesWereRemoved or fontZonesWereReplaced:
            fl.GenerateFont(eval("ftTYPE1ASCII"), pfaPathTemp)
            fl.Close(fl.ifont)
            fl.Open(pfaPathTemp)
            if os.path.exists(infPathTemp): # Delete the .INF file (bug in FL v5.1.x)
                os.remove(infPathTemp)
    
        addNULLandCRglyphs()
        
        # Load encoding file
        fl.font.encoding.Load(encPath)
        
        # Make sure the Font window is in 'Names mode'
        fl.CallCommand(fl_cmd.FontModeNames)
    
        # Sort glyphs by encoding
        fl.CallCommand(fl_cmd.FontSortByCodepage)
        
        # read derivedchars file, make components
        if makeDV:
            dvInput_module.run(verbose = False)
        
        convertT1toTT()
        changeTTfontSettings()
        
        # Switch the Font window to 'Index mode'
        fl.CallCommand(fl_cmd.FontModeIndex)
        
        folderPath, fontFileName = os.path.split(pfaPath)  # path to the folder where the font is contained and the font's file name
        ppmsFilePath = os.path.join(folderPath, kPPMsFileName)
        if os.path.exists(ppmsFilePath):
            readPPMsFile(ppmsFilePath)
            replaceStemsAndPPMs()
         
        tthintsFilePath = os.path.join(folderPath, kTTHintsFileName)
        if os.path.exists(tthintsFilePath):
            InputTrueTypeHints.run(folderPath, coord_option=False)
            # readTTHintsFile(tthintsFilePath)
            # replaceTTHints()
         
      # ttfPath = pfaPath.replace('.pfa','.ttf')
        ttfPath = os.path.join(folderPath, kFontTTF) # The filename of the TT output is hardcoded
        fl.GenerateFont(eval("ftTRUETYPE"), ttfPath)
        
        vfbPath = pfaPath.replace('.pfa','.vfb')
        fl.Save(vfbPath)
        
        fl.font.modified = 0    
        fl.Close(fl.ifont)

        # The TT font generated with FontLab ends up with a few glyph names changed
        # Fix the glyph names so that makeOTF does not fail
        # Do not proceed if something went wrong with the glyph renaming process
        if not fixGlyphNames(ttfPath):
            print "ERROR: Failed to post-process the TrueType file."
            return
        
        # Delete temporary Encoding file
        if os.path.exists(encPath):
            os.remove(encPath)

        # Delete temp PFA
        if os.path.exists(pfaPathTemp):
            os.remove(pfaPathTemp)
        
        # Cleanup after processing from TXT type1 font or UFO font
        if fontIsTXT or fontIsUFO:
            if os.path.exists(pfaPath):
                os.remove(pfaPath)
            if os.path.exists(ttfPath):
                finalTTFpath = ttfPath.replace('_TEMP_.ttf','.ttf')
                os.rename(ttfPath, finalTTFpath)
            if os.path.exists(vfbPath):
                finalVFBpath = vfbPath.replace('_TEMP_.vfb','.vfb')
                os.rename(vfbPath, finalVFBpath)


def run():
    # Get folder to process
    baseFolderPath = fl.GetPathName("Select font family directory")
    if not baseFolderPath: # Cancel was clicked or Esc key was pressed
        return

    startTime = time.time()  # Initiates a timer of the whole process

    fontsList = getFontPaths(baseFolderPath)
    print fontsList
    return

    if len(fontsList):
        processFonts(fontsList)
    else:
        print "No fonts found"
    
    endTime = time.time()
    elapsedSeconds = endTime-startTime

    if (elapsedSeconds/60) < 1:
        print '\nCompleted in %.1f seconds.\n' % elapsedSeconds
    else:
        print '\nCompleted in %s minutes and %s seconds.\n' % (elapsedSeconds/60, elapsedSeconds%60)

    # print "Conversion options:"
    # print '\n'.join(conversionOptions)
    # if stemsAndPPMsEdited:
    #     print "Stems and PPMs edited"
    # if ttHintsEdited:
    #     print "TT glyph hints edited"


if __name__ == "__main__":
    run()
