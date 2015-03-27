#FLM: TT Hints Duplicator
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
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING 
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
DEALINGS IN THE SOFTWARE.

"""


__doc__ = u'''

DESCRIPTION:
------------

This script was created to duplicate TT hints information across compatible
styles of a typeface, cutting the time needed for TT hinting by a significant
amount. The script is to be run from within FontLab, and does not need any
of the involved fonts to be open.



IMPORTANT: 
----------

1) 
This script will not process delta-hints.

2)
The script can only process TT instructions that are attached to *on-curve* 
points, because those are the only ones that will have the same coordinates
in both PS and TT outlines.

3)
It is expected that overlaps are removed in the source CFF and TTF files. This
ensures outline predictability.
Depending on the drawing it can mean that there is some work to be done for 
compatibilizing the outlines, which is usually less work than hinting it.



PROCESS:
--------

This workflow relies on the Adobe style for building fonts, which means using
a tree of folders, with one folder per style. In those folders, various files
are expected:

    - one source file per folder, which has CFF (PS) outlines.        
      Multiple formats are possible: `font.ufo` OR `font.pfa` OR `font.txt`
      
    - one file per folder with TTF outlines, created from above source file,
      named `font.ttf`

    - one template `tthints` file, which is created by hinting one style,
      and exporting the hints with e.g. OutputTrueTypeHintsPlus.py


An example tree could look like this - in this case, the source files are UFOs,
and the Regular style has been hinted by hand (in the VFB file). Then, a `tthints`
file has been exported from the Regular:

    Roman
        │
        ├─ Light
        │   │
        │   ├─ font.ttf
        │   └─ font.ufo
        │
        ├─ Regular
        │   │
        │   ├─ font.ttf
        │   ├─ font.ufo
        │   ├─ font.vfb
        │   └─ tthints
        │
        └─ Bold
            │
            ├─ font.ttf
            └─ font.ufo



This script will generate `tthints` files for all the other styles within the 
same (compatible) family, which can then be applied via `InputTrueTypeHints.py`



BACKGROUND INFO:
----------------

When PS outlines are converted to TT outlines, the number of points on a given
glyph  is not always the same for all instances (even when generated from the
same MM font). As a result, the "tthints" files created for one instance cannot
simply be reused as-is  with another instance. What this script does is taking a
note of points which TT  instructions are attached to,  and correlate them with
the points in the original PS font. This info can be used for finding  new point
indexed for any given on-curve point in a  related TrueType instance.


See the Robothon talk on this problem here: 
    http://typekit.files.wordpress.com/2012/04/truetype_hinting_robothon_2012.pdf
    http://vimeo.com/38352194



KNOWN ISSUES: 
-------------

1)
At the time of writing (December 2014), FontLab has a bug within OSX Yosemite,
which makes executing external code impossible. Since this script uses the `tx`
command to convert to and from PFA, this is a problem.

The solution is opening FontLab not from the Finder, but from the command line, 
like this:

    open "/Applications/FontLab Studio 5.app"

In-depth description of this problem: 
http://forum.fontlab.com/index.php?topic=9134.0



2)
os.popen is used to call tx and ttx.
It is true -- `os.popen` is deprecated; but any attempt to modernize this part
of the code just resulted in horrible crashes and (no kidding) kernel panics.

'''


import sys
import os
import time
import itertools
from FL import *
from robofab.world import CurrentFont 
from robofab.objects.objectsRF import RFont
'The RFont object from robofab.world is not appropriate in this case, because it makes a new FL font.'

fl.output = ''
MAC = False
PC  = False

if sys.platform in ('mac', 'darwin'): MAC = True
elif os.name == 'nt': PC = True

'Adding the FDK Path to the env variable (on Mac only) so that command line tools can be called from FontLab'
if MAC:
    fdkPathMac = os.sep.join((os.path.expanduser('~'), 'bin', 'FDK', 'tools', 'osx'))
    envPath = os.environ["PATH"]
    newPathString = envPath + ":" + fdkPathMac
    if fdkPathMac not in envPath:
        os.environ["PATH"] = newPathString



# numerical identifiers for different kinds of hints 
vAlignLinkTop = 1
vAlignLinkBottom = 2
hSingleLink = 3
vSingleLink = 4
hDoubleLink = 5
vDoubleLink = 6
hAlignLinkNear = 7
vAlignLinkNear = 8
hInterpolateLink = 13
vInterpolateLink = 14
hMidDelta = 20
vMidDelta = 21
hFinDelta = 22
vFinDelta = 23

deltas = [hMidDelta, hFinDelta, vMidDelta, vFinDelta]
interpolations = [hInterpolateLink, vInterpolateLink]
links = [hSingleLink, hDoubleLink, vSingleLink, vDoubleLink]
alignments = [vAlignLinkTop, vAlignLinkNear, vAlignLinkBottom, hAlignLinkNear]


kTTFFileName = "font.ttf"
kPFAFileName = "font.pfa"
kTXTFileName = "font.txt"
kUFOFileName = "font.ufo"
kTTHintsFileName = "tthints"

folderPathsList = []
templateTTHintsList = []
templateGlyphNodeIndexDict = {}
okToProcessTargetFonts = True



# -----------

'Code for identifying segment intersection:'
class Point:
    def __init__(self,x,y):
        self.x = x
        self.y = y

def ccw(A,B,C):
    return (C.y-A.y)*(B.x-A.x) > (B.y-A.y)*(C.x-A.x)

def segmentsIntersect(seg1, seg2):
    # http://www.bryceboe.com/2006/10/23/line-segment-intersection-algorithm/
    A,B = Point(seg1[0][0],seg1[0][1]), Point(seg1[1][0],seg1[1][1])
    C,D = Point(seg2[0][0],seg2[0][1]), Point(seg2[1][0],seg2[1][1])
    return ccw(A,C,D) != ccw(B,C,D) and ccw(A,B,C) != ccw(A,B,D)

# -----------


class myHintedNode:
    def __init__(self, nodeXpos, nodeYpos, nodeIndexTT, nodeIndexT1):
        self.nodeXpos = nodeXpos
        self.nodeYpos = nodeYpos
        self.nodeIndexTT = nodeIndexTT
        self.nodeIndexT1 = nodeIndexT1


def getGlyphOncurveCoords(glyph):
    'Collects on-curve coordinates for all contours of a given glyph.'
    glyphCoordsDict = {}
    for contourIndex in range(len(glyph)):
        contour = glyph[contourIndex]
        pointsList = []
        testList = []
        for pt in contour.bPoints:
            pointsList.append(pt.anchor)

        if len(pointsList) > 2 and pointsList[0] == pointsList[-1]:
            # Post-processing pointsList:
            # Sometimes (not always,) FL will add the start point at both position 0 and -1.
            # If that happens, the last point will be removed from the list.
            pointsList.pop()

        glyphCoordsDict[contourIndex] = pointsList
    return glyphCoordsDict


def getSegmentsList(ptDict1, ptDict2):
    'Creates lists of individual segments and compares their length across glyphs.'
    segmentsList = []
    for i in ptDict1.keys():
        for j in range(len(ptDict1[i])):
            try: # If the contours are out of order, a "IndexError: list index out of range" may happen
                segmentsList.append([ ptDict1[i][j], ptDict2[i][j] ])
            except:
                return # contour mismatch found
    return segmentsList


def closeAllOpenedFonts():
    for i in range(len(fl))[::-1]: # [::-1] reverses the list
        fl.Close(i)


def getFolderPaths(path, startpath):
    if (path != templateFolderPath
        and (os.path.exists(os.path.join(path, kPFAFileName)) 
        or os.path.exists(os.path.join(path, kTXTFileName)) 
        or os.path.exists(os.path.join(path, kUFOFileName)))
        and os.path.exists(os.path.join(path, kTTFFileName))):
            folderPathsList.append(path)
    else:
        files = os.listdir(path)
        for file in files:
            if os.path.isdir(os.path.join(path, file)):
                getFolderPaths(os.path.join(path, file), startpath)


def saveNewTTHintsFile(folderPath, content):
    filePath = os.path.join(folderPath, kTTHintsFileName)
    outfile = open(filePath, 'w')
    outfile.writelines(content)
    outfile.close()


def readTTHintsFile(filePath):
    file = open(filePath, "r")
    data = file.read()
    file.close()
    lines = data.splitlines()

    # Empty TTHints list
    del templateTTHintsList[:]
    
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
            templateTTHintsList.append(line)


def collectT1nodeIndexes(gName, t1font):
    gIndex = t1font.FindGlyph(gName)
    if gIndex != -1:
        glyph = t1font[gName]
    else:
        print "ERROR: Glyph %s not found in PS font." % gName
        return

    nodesDict = {}
    
    if glyph.nodes: # Just making sure that there's an outline in there...
        for nodeIndex in range(len(glyph)):
            if glyph.nodes[nodeIndex].type != nOFF: # Ignore off-curve nodes
                nodeCoords = "%s,%s" % (glyph.nodes[nodeIndex].x, glyph.nodes[nodeIndex].y)
                if nodeCoords not in nodesDict:
                    nodesDict[nodeCoords] = nodeIndex

    return nodesDict, len(glyph)


def collectTTnodeIndexes(gName, ttfont):
    gIndex = ttfont.FindGlyph(gName)
    if gIndex != -1:
        glyph = ttfont[gName]
    else:
        print "ERROR: Glyph %s not found in target TT font." % gName
        return

    nodesDict = {}
    
    if glyph.nodes: # Just making sure that there's an outline in there...
        for nodeIndex in range(len(glyph)):
            if glyph.nodes[nodeIndex].type != nOFF: # Ignore off-curve nodes
                nodeCoords = "%s,%s" % (glyph.nodes[nodeIndex].x, glyph.nodes[nodeIndex].y)
                if nodeCoords not in nodesDict:
                    nodesDict[nodeCoords] = nodeIndex
                else:
                    print "ERROR: Overlapping node found in glyph %s at %s." % (gName, nodeCoords)

    return nodesDict


def collectTemplateIndexes(tthintsFilePath, ttfont, t1font):
    readTTHintsFile(tthintsFilePath)

    for line in templateTTHintsList:
        gName, gHints = line.split() 
        # dollar   6,72,56,0;6,13,28,0;6,111,76,0;6,32,97,0;4,56,42,-1,-1;4,13,86,-1,-1;4,72,87,-1,-1;4,28,101,-1,-1

        gIndex = ttfont.FindGlyph(gName)
        if gIndex != -1:
            glyph = ttfont[gName]
        else:
            print "ERROR: Glyph %s not found in TT font." % gName
            continue

        t1GlyphNodeIndexDict, t1GlyphNodesCount = collectT1nodeIndexes(gName, t1font) 
        # This dictionary is indexed by the combination of the coordinates of each node of the current glyph
        
        hintedNodesDict = {} # This dictionary is indexed by the node indexes of the template TT font
        gHintsList = gHints.split(';')

        for commandString in gHintsList:
            commandList = list(eval(commandString))
            commandType = commandList[0]

            if len(commandString):
                if commandType in deltas:
                    print "Delta hints like (%s : %s) are not transferred. Skipping hint..." % (gName, commandString)
                elif commandType in links:
                    nodes = commandList[1:3]
                elif commandType in alignments + interpolations:
                    nodes = commandList[1:-1]
                else:
                    print "WARNING: Hint type %d in glyph %s is not supported." % (commandType, gName)
                    continue
                
                for hintedNodeIndex in nodes:
                    node = ttfont[gIndex][hintedNodeIndex]
                    try:
                        node.type
                    except:
                        print "ERROR: Hinting problem in glyph %s. Skipping..." % gName
                        okToProcessTargetFonts = False
                        continue

                    if node.type != nOFF: # Ignore off-curve nodes in TrueType
                        nodeCoords = "%s,%s" % (node.x, node.y)
                        if nodeCoords in t1GlyphNodeIndexDict:
                            t1NodeIndex = t1GlyphNodeIndexDict[nodeCoords]
                            hintedNode = myHintedNode(node.x, node.y, hintedNodeIndex, t1NodeIndex)
                            if hintedNodeIndex not in hintedNodesDict:
                                hintedNodesDict[hintedNodeIndex] = hintedNode
                        else:
                            print "ERROR: Could not find an on-curve node at %s in the PS font." % nodeCoords
                    else:
                        print "Node #%d in glyph %s is off-curve. Skipping..." % (hintedNodeIndex, gName)
                
        templateGlyphNodeIndexDict[gName] = [hintedNodesDict, t1GlyphNodesCount]


def getNewTTindexes(glyph, nodeIndexList, ttGlyphNodeIndexDict):
    newTTindexesList = []
    templateTTdict = templateGlyphNodeIndexDict[glyph.name][0]

    for templateTTindex in nodeIndexList:
        templateT1index = int(templateTTdict[templateTTindex].nodeIndexT1)
        targetT1nodeCoords = "%d,%d" % (glyph.nodes[templateT1index].x, glyph.nodes[templateT1index].y)
        if targetT1nodeCoords in ttGlyphNodeIndexDict:
            newTTindexesList.append(ttGlyphNodeIndexDict[targetT1nodeCoords])
        else:
            print "Could not find target node in %s." % glyph.name

    return newTTindexesList


def processTargetFonts(tthintsFilePath, templateT1RBfont):
    totalFolders = len(folderPathsList)
    print "%d folders found" % totalFolders
    
    fontIndex = 1
    for targetFolderPath in folderPathsList:
        deleteTempPFA = False
        targetFolderName = os.path.basename(targetFolderPath)

        pfaFilePath = os.path.join(targetFolderPath, kPFAFileName)
        txtFilePath = os.path.join(targetFolderPath, kTXTFileName)
        ufoFilePath = os.path.join(targetFolderPath, kUFOFileName)

        if os.path.exists(pfaFilePath):
            pass
        elif os.path.exists(txtFilePath):
            deleteTempPFA = True
            makePFAfromTXT(txtFilePath, pfaFilePath)
        elif os.path.exists(ufoFilePath):
            deleteTempPFA = True
            makePFAfromUFO(ufoFilePath, pfaFilePath)
        else:
            print "ERROR: Could not find target %s/%s file. Skipping %s folder..." % (kPFAFileName, kTXTFileName, targetFolderName)
            continue
        
        ttfFilePath = os.path.join(targetFolderPath, kTTFFileName)
        if not os.path.exists(ttfFilePath):
            print "ERROR: Could not find target %s file. Skipping %s folder..." % (kTTFFileName, targetFolderName)
            continue
        
        print "\nProcessing %s ... (%d/%d)" % (targetFolderName, fontIndex, totalFolders)
        fontIndex += 1
        
        fl.Open(pfaFilePath)
        targetT1font = fl[fl.ifont]
        targetT1RBfont = CurrentFont()
        fl.Open(ttfFilePath)
        targetTTfont = fl[fl.ifont]
        
        newTTHintsFileList = ["#Glyph name\tTT hints\tGlyph color\n"]
        
        for line in templateTTHintsList: # this list was assembled earlier
            gName, gHints = line.split() # dollar   6,72,56,0;6,13,28,0;6,111,76,0;6,32,97,0;4,56,42,-1,-1;4,13,86,-1,-1;4,72,87,-1,-1;4,28,101,-1,-1
            gMark = None
    
            gIndex = targetT1font.FindGlyph(gName)
            if gIndex != -1:
                glyph = targetT1font[gName]
            else:
                print "ERROR: Glyph %s not found in target PS font." % gName
                continue
            
            # Test outline compatibility between the two glyphs (template and target)
            templateT1RBglyph = templateT1RBfont[gName]
            targetT1RBglyph = targetT1RBfont[gName]
            if not templateT1RBglyph.isCompatible(targetT1RBglyph, False): # (NOTE: This method doesn't catch the case where the node indexes have rotated)
                print "DEFINITELY NOT COMPATIBLE: %s. Skipping..." % gName
                continue
    
            # Check that the glyph in the template T1 font has the same number of nodes as the target T1 font.
            # Although the two fonts should be compatible, if the MM font had overlapping nodes, those will
            # be flattened into a single node when the instance gets processed through CheckOutlines
          # if (templateGlyphNodeIndexDict[glyph.name][1] != len(glyph)):
          #     print "ERROR: The PS glyph %s does not have the same number of nodes as the template PS font. Skipping...\n\tPlease check for overlapping nodes in the MM source." % (glyph.name)
          #     continue
            
            # Do a second level of compatibility verification
            ptDict1 = getGlyphOncurveCoords(templateT1RBglyph) # Make a dictionary of the coodinates of on-curve points
            ptDict2 = getGlyphOncurveCoords(targetT1RBglyph)
            segmentsList = getSegmentsList(ptDict1, ptDict2) # Define segments using the point coordinates from ptDict1 and ptDict2

            if not segmentsList:
                print "DEFINITELY NOT COMPATIBLE (contour mismatch): %s. Skipping..." % gName
                continue

            segmentCombinationsList = list(itertools.combinations(segmentsList, 2)) # Get all pair combinations of those segments
            # Iterate through the segment combinations and stop as soon as an intersection between two segments is found
            for combination in segmentCombinationsList:
                seg1, seg2 = combination[0], combination[1]
                if segmentsIntersect(seg1, seg2):
                    print "POSSIBLY NOT COMPATIBLE: %s. Please check..." % gName
                    gMark = 25 # orange
                    break # one incompatibility was found; no need to report it more than once
            
            ttGlyphNodeIndexDict = collectTTnodeIndexes(gName, targetTTfont) # This dictionary is indexed by the combination of the coordinates of each node of the current glyph
            gHintsList = gHints.split(';')
            newHintsList = []

            for commandString in gHintsList:
                newHintCommand = []
                commandList = list(eval(commandString))
                commandType = commandList[0]

                if len(commandList):
                    newHintCommand.append(commandType)

                    if commandType in deltas:
                        continue

                    elif commandType in alignments:
                        nodes = [commandList[1]]
                        targetNodeIndexList = getNewTTindexes(glyph, nodes, ttGlyphNodeIndexDict)
                        hintParamsList = [commandList[-1]]

                    elif commandType in links:
                        nodes = commandList[1:3]
                        targetNodeIndexList = getNewTTindexes(glyph, nodes, ttGlyphNodeIndexDict)
                        hintParamsList = commandList[3:]

                    elif commandType in interpolations:
                        nodes = commandList[1:-1]
                        targetNodeIndexList = getNewTTindexes(glyph, nodes, ttGlyphNodeIndexDict)
                        hintParamsList = [commandList[-1]]

                newCommandList = [commandType] + targetNodeIndexList + hintParamsList
                newHint = ','.join(map(str, newCommandList))
                newHintsList.append(newHint)


            newHintsLine = "%s\t%s" % (gName, ';'.join(newHintsList))
            if gMark:
                newHintsLine = "%s\t%s" % (newHintsLine, gMark)
            newTTHintsFileList.append(newHintsLine + "\n")

        saveNewTTHintsFile(targetFolderPath, newTTHintsFileList)
        closeAllOpenedFonts()
        
        if deleteTempPFA:
            if os.path.exists(pfaFilePath):
                os.remove(pfaFilePath)


def makePFAfromTXT(txtFilePath, pfaFilePath):
    if MAC:
        type1Tool = "type1"
    if PC:
        type1Tool = "type1.exe"

    command = "%s '%s' > '%s'" % (type1Tool, txtFilePath, pfaFilePath)
    
    # Run type1 tool
    if MAC:
        pp = os.popen(command)
        report = pp.read()
        pp.close()
    if PC:
        pp = Popen(command)


def makePFAfromUFO(ufoFilePath, pfaFilePath):
    if MAC:
        txTool = "tx"
    if PC:
        txTool = "tx.cmd"

    command = "%s -t1 '%s' > '%s'" % (txTool, ufoFilePath, pfaFilePath)
    
    # Run tx tool
    if MAC:
        pp = os.popen(command)
        report = pp.read()
        pp.close()
    if PC:
        pp = Popen(command)


def run():
    global templateFolderPath
    templateFolderPath = fl.GetPathName("Select directory that contains the 'tthints' template file...")
    
    # Cancel was clicked or ESC key was pressed
    if not templateFolderPath:
        return

    # Verify that the files tthints, font.pfa/ufo and font.ttf exist in the folder provided
    tthintsFilePath = os.path.join(templateFolderPath, kTTHintsFileName)
    if not os.path.exists(tthintsFilePath):
        print "ERROR: Could not find %s file." % kTTHintsFileName
        return

    pfaFilePath = os.path.join(templateFolderPath, kPFAFileName)
    txtFilePath = os.path.join(templateFolderPath, kTXTFileName)
    ufoFilePath = os.path.join(templateFolderPath, kUFOFileName)

    if os.path.exists(pfaFilePath):
        pass
    elif os.path.exists(txtFilePath):
        pass
    elif os.path.exists(ufoFilePath):
        pass
    else:
        print "ERROR: Could not find any of the following font files: %s, %s or %s." % (kPFAFileName, kTXTFileName, kUFOFileName)
        return

    ttfFilePath = os.path.join(templateFolderPath, kTTFFileName)
    if not os.path.exists(ttfFilePath):
        print "ERROR: Could not find %s file." % kTTFFileName
        return

    global baseFolderPath
    baseFolderPath = fl.GetPathName("Select top directory that contains the fonts to process...")
    
    # Cancel was clicked or Esc key was pressed
    if not baseFolderPath:
        return

    getFolderPaths(baseFolderPath, baseFolderPath)

    startTime = time.time()  # Initiates a timer of the whole process


    if len(folderPathsList):
        deleteTemplateTempPFA = False
        print "Processing template files..."
        fl.Open(ttfFilePath)
        templateTTfont = fl[fl.ifont]
        if not os.path.exists(pfaFilePath) and os.path.exists(txtFilePath):
            deleteTemplateTempPFA = True
            makePFAfromTXT(txtFilePath, pfaFilePath)
        elif not os.path.exists(pfaFilePath) and os.path.exists(ufoFilePath):
            deleteTemplateTempPFA = True
            makePFAfromUFO(ufoFilePath, pfaFilePath)
        fl.Open(pfaFilePath)
        templateT1font = fl[fl.ifont]
        # Make a Robofab font of the Type1 template font. This RB font is made by copying each glyph.
        # There doesn't seem to exist a simpler method that produces reliable results. 
        # The challenge comes from having to close the FL font downstream.
        templateT1RBfont = RFont()
        currentT1RBfont = CurrentFont()
        for g in currentT1RBfont:
            templateT1RBfont.insertGlyph(g)

        collectTemplateIndexes(tthintsFilePath, templateTTfont, templateT1font)
        closeAllOpenedFonts()
        
        if okToProcessTargetFonts:
            processTargetFonts(tthintsFilePath, templateT1RBfont)
        else:
            print "Can't process target fonts because of hinting errors found in template font."
        
        if deleteTemplateTempPFA:
            if os.path.exists(pfaFilePath):
                os.remove(pfaFilePath)

    else:
        print "Could not find suitable folders to process."
    

    endTime = time.time()
    elapsedSeconds = endTime-startTime
    
    if (elapsedSeconds/60) < 1:
        print '\nCompleted in %.1f seconds.\n' % elapsedSeconds
    else:
        print '\nCompleted in %s minutes and %s seconds.\n' % (elapsedSeconds/60, elapsedSeconds%60)


if __name__ == "__main__":
    run()
