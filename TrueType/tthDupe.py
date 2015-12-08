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
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.

"""

__doc__ = u'''
TT Hints Duplicator

This script was written to duplicate TT hinting data across compatible styles
of a typeface family, cutting the time needed for TT hinting by a significant
amount. The script is run as a FontLab macro, and does not need any of the
involved fonts to be open.

The script duplicates `tthints` files by reading information from the source
`tthints` file and associated fonts, and comparing this data to the target
fonts. It will not modify source- or target fonts in any way.

The script is smart enough to not re-process the source folder, so it is safe
to pick the root of a font project as the target directory.


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

v1.5 - Dec 07 2015 - Point out major incompatibilities between TTF and CFF
                     outlines, and do not duplicate recipes for those glyphs.
v1.4 - Apr 18 2015 - Support reading instructions defined with point coordinates.
                     Add option to save instructions using point coordinates.
v1.3 - Apr 02 2015 - Now also works in FL Windows.
v1.2 - Mar 29 2015 - Speed improvement by reading/writing only glyphs listed
                     in the tthints file.
v1.1 - Mar 23 2015 - Support duplication of instructions in both directions.
v1.0 - Mar 04 2015 - First public release (Robothon 2015).
'''


import sys
import os
import time
import itertools
from FL import *
from robofab.world import CurrentFont
from robofab.objects.objectsRF import RFont
'''(The RFont object from robofab.world is not appropriate \
in this case, because it would create a new FL font.)'''

fl.output = ''

MAC = False
PC  = False
if sys.platform in ('mac', 'darwin'):
    MAC = True
elif os.name == 'nt':
    PC = True

'Adding the FDK Path to the env variable (on Mac only) so that command line tools can be called from FontLab'
if MAC:
    fdkPathMac = os.sep.join((os.path.expanduser('~'), 'bin', 'FDK', 'tools', 'osx'))
    envPath = os.environ["PATH"]
    newPathString = envPath + ":" + fdkPathMac
    if fdkPathMac not in envPath:
        os.environ["PATH"] = newPathString

if PC:
    from subprocess import Popen, PIPE

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


class MyHintedNode:
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
            # Post-process the pointsList:
            # Depending on the position of the start point, FL may store it
            # at both position 0 and -1. If that happens, the final (dupliacted)
            # point will be removed from the list.
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


def getFolderPaths(path, templatePath):
    '''
    Returns any folder that contains either of the possible input fonts
    (PFA, TXT, or UFO) and an adjactent TTF -- except the template folder.
    '''

    folderPathsList = []

    for root, dirs, files in os.walk(path):
        PFApath = os.path.join(root, kPFAFileName)
        TXTpath = os.path.join(root, kTXTFileName)
        UFOpath = os.path.join(root, kUFOFileName)
        TTFpath = os.path.join(root, kTTFFileName)

        if (os.path.exists(TTFpath)
            and (os.path.exists(PFApath)
                or os.path.exists(TXTpath)
                or os.path.exists(UFOpath))):

                    if root != templatePath:
                        folderPathsList.append(root)

    return folderPathsList


def saveNewTTHintsFile(folderPath, contentList):
    filePath = os.path.join(folderPath, kTTHintsFileName)
    outfile = open(filePath, 'w')
    outfile.writelines(contentList)
    outfile.close()


def readTTHintsFile(filePath):
    '''
    Reads a tthints file, and returns a tuple:
    - a list storing the glyph order of the input file
    - a dict {glyph name: raw hinting string}
    '''

    tthfile = open(filePath, "r")
    tthdata = tthfile.read()
    tthfile.close()
    lines = tthdata.splitlines()

    glyphList = []
    rawHintingDict = {}

    for line in lines:
        # Skip over blank lines
        stripline = line.strip()
        if not stripline:
            continue
        # Get rid of all comments
        if stripline[0] == '#':
            continue
        else:
            if len(line.split()) >= 2:
                gName = line.split()[0]
                gHintingString = line.split()[1]
                glyphList.append(gName)
                rawHintingDict[gName] = gHintingString

    return glyphList, rawHintingDict


def collectT1nodeIndexes(gName, t1font):
    gIndex = t1font.FindGlyph(gName)
    if gIndex != -1:
        glyph = t1font[gName]
    else:
        print "ERROR: Glyph %s not found in PS font." % gName
        return

    nodesDict = {}

    if glyph.nodes: # Just making sure that there's an outline in there ...
        for nodeIndex in range(len(glyph)):
            if glyph.nodes[nodeIndex].type != nOFF: # Ignore off-curve nodes
                nodeCoords = (glyph.nodes[nodeIndex].x, glyph.nodes[nodeIndex].y)
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
                nodeCoords = (glyph.nodes[nodeIndex].x, glyph.nodes[nodeIndex].y)
                if nodeCoords not in nodesDict:
                    nodesDict[nodeCoords] = nodeIndex
                else:
                    print "ERROR: Overlapping node found in glyph %s at %s." % (gName, nodeCoords)

    return nodesDict


def transformCommandList(glyph, raw_commandList):
    '''
    Transforms a list of commands with point coordinates
    to an list of commands with point indexes, for instance:

        input:  [4, (155, 181), (180, 249), 0, -1]
        output: [4, 6, 9, 0, -1]

        input:  [3, 'BL', (83, 0), 0, -1]
        output: [3, 34, 0, 0, -1]

    Also is used to check validity of point coordinates, and
    transforming sidebearing flags to point indexes.

    '''

    # pointDict = {(point.x, point.y): pointIndex for pointIndex, point in enumerate(glyph.nodes)}
    pointDict = dict(((point.x, point.y), pointIndex) for pointIndex, point in enumerate(glyph.nodes))

    output = []
    for item in raw_commandList:
        if item == 'BL':
            'left sidebearing hinted'
            output.append(len(glyph))
        elif item == 'BR':
            'right sidebearing hinted'
            output.append(len(glyph) + 1)
        elif isinstance(item, tuple):
            'point coordinates'
            pointIndex = pointDict.get(item, None)
            if pointIndex == None:
                print '\tERROR: point %s does not exist in glyph %s.' % (item, glyph.name)
            output.append(pointIndex)
        else:
            'other hinting data, integers'
            output.append(item)

    if None in output:
        return []
    else:
        return output


def collectTemplateIndexes(ttfont, t1font, glyphList, rawHintingDict):
    '''
    Creates a dictionary from template font files and the template tthints file.

        keys:   glyph names for all hinted glyphs
        values: a dictionary of point indexes as keys, and MyHintedNode instances as values.
                MyHintedNode contains x, y, templateTTIndex, templateT1Index for a given point.

    '''
    okToProcessTargetFonts = True
    outputDict = {}
    indexOnlyRawHintingDict = {}

    for gName in glyphList:
        writeGlyphRecipe = True

        gIndex = ttfont.FindGlyph(gName)
        if gIndex != -1:
            glyph = ttfont[gName]
        else:
            print "ERROR: Glyph %s not found in TT font." % gName
            continue

        # This dictionary is indexed by the combination of the coordinates of each node of the current glyph:
        t1GlyphNodeIndexDict, t1GlyphNodesCount = collectT1nodeIndexes(gName, t1font)

        hintedNodesDict = {} # This dictionary is indexed by the node indexes of the template TT font
        gHintsString = rawHintingDict[gName]
        gHintsList = gHintsString.split(";")
        indexOnlyRawHintingList = []

        for commandString in gHintsList:
            raw_commandList = list(eval(commandString))
            commandType = raw_commandList[0]
            commandList = transformCommandList(glyph, raw_commandList)

            if not commandList:
                print "ERROR: Problems with reading recipe of glyph %s" % (gName)
                writeGlyphRecipe = False
                break

            if len(commandList) < 3:
                print "ERROR: A hint definition for glyph %s does not have enough parameters: %s" % (gName, commandString)
                writeGlyphRecipe = False
                break

            if commandType in deltas:
                print "INFO: Delta hints are not transferred. Skipping hint (%s) in %s ..." % (commandString, gName)
            elif commandType in links:
                nodes = commandList[1:3]
            elif commandType in alignments + interpolations:
                nodes = commandList[1:-1]
            else:
                print "WARNING: Hint type %d in glyph %s is not supported." % (commandType, gName)
                continue

            indexOnlyRawHintingList.append(','.join(map(str,commandList)))

            for hintedNodeIndex in nodes:
                targetGlyph = ttfont[gIndex]
                node = targetGlyph[hintedNodeIndex]
                sidebearingIndexes = [len(targetGlyph), len(targetGlyph)+1]

                try:
                    node.type
                    # This check makes sure that a referenced node index actually exist
                    # in an outline. However, it also skips any glyphs with hinted
                    # sidebearings, because those 'nodes' are represented as len(glyph),
                    # and len(glyph)+1.

                except:
                    if hintedNodeIndex in sidebearingIndexes:
                        print "ERROR: Sidebearings have been hinted in %s, which is not (yet) supported. Skipping glyph ..." % gName
                    else:
                        print "ERROR: Hinting problem in %s. Skipping glyph ..." % gName

                    okToProcessTargetFonts = False
                    continue

                if node.type == nOFF:
                    # Ignore off-curve nodes in TrueType, do not write glyph recipe to the output file
                    print "Node #%d in glyph %s is off-curve. Skipping glyph ..." % (hintedNodeIndex, gName)
                    writeGlyphRecipe = False
                    break

                else:
                    nodeCoords = (node.x, node.y)
                    if nodeCoords in t1GlyphNodeIndexDict:
                        t1NodeIndex = t1GlyphNodeIndexDict[nodeCoords]
                        hintedNode = MyHintedNode(node.x, node.y, hintedNodeIndex, t1NodeIndex)
                        if hintedNodeIndex not in hintedNodesDict:
                            hintedNodesDict[hintedNodeIndex] = hintedNode
                    else:
                        print "ERROR in %s: Could not find an on-curve point at (%s) in the PS font." % (gName, ', '.join(map(str, nodeCoords)))

        if writeGlyphRecipe:
            outputDict[gName] = hintedNodesDict
            indexOnlyRawHintingDict[gName] = ';'.join(indexOnlyRawHintingList)

    return outputDict, indexOnlyRawHintingDict, okToProcessTargetFonts


def getNewTTindexes(glyph, nodeIndexList, ttGlyphNodeIndexDict, rawHintingDict):
    newTTindexesList = []
    newTTcoordsList = []
    templateTTdict = rawHintingDict[glyph.name]

    for templateTTindex in nodeIndexList:
        try:
            templateT1index = int(templateTTdict[templateTTindex].nodeIndexT1)
        except KeyError:
            templateT1index = None
            print 'INFO: Major incompatibility (TTF vs CFF) in glyph %s.' % glyph.name
            return

        if templateT1index != None:
            try:
                targetT1nodeCoords = (glyph.nodes[templateT1index].x, glyph.nodes[templateT1index].y)
            except IndexError:
                # Again, FontLab's fantastic ability to make a contour longer than it is, by re-inserting
                # the first point a second time in position -1. In this case, the templateT1index is
                # re-set to be the first point of the last contour, which makes no functional difference.
                if templateT1index == len(glyph):
                    numberOfCountours = glyph.GetContoursNumber()
                    firstPointOfLastContour = glyph.GetContourBegin(numberOfCountours-1)
                    templateT1index = firstPointOfLastContour
                    targetT1nodeCoords = (glyph.nodes[templateT1index].x, glyph.nodes[templateT1index].y)
                else:
                    print 'I give up.'

            if targetT1nodeCoords in ttGlyphNodeIndexDict:
                newTTindexesList.append(ttGlyphNodeIndexDict[targetT1nodeCoords])
                newTTcoordsList.append(targetT1nodeCoords)
            else:
                print "Could not find target node in %s." % glyph.name
                # It is probably better to not write the remaning hinting recipe for a
                # given glyph at all if one of its points is not found in the target TTF.
                return

    return newTTindexesList, newTTcoordsList


def processTargetFonts(folderPathsList, templateT1RBfont, hintedNodeDict, glyphList, rawHintingDict, writeCoordinates):
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
            print "ERROR: Could not find target %s/%s file. Skipping %s folder ..." % (kPFAFileName, kTXTFileName, targetFolderName)
            continue

        ttfFilePath = os.path.join(targetFolderPath, kTTFFileName)
        if not os.path.exists(ttfFilePath):
            print "ERROR: Could not find target %s file. Skipping %s folder ..." % (kTTFFileName, targetFolderName)
            continue

        print "\nProcessing %s ... (%d/%d)" % (targetFolderName, fontIndex, totalFolders)
        fontIndex += 1

        fl.Open(pfaFilePath)
        targetT1font = fl[fl.ifont]
        targetT1RBfont = CurrentFont()
        fl.Open(ttfFilePath)
        targetTTfont = fl[fl.ifont]

        newTTHintsFileList = ["# Glyph name\tTT hints\tGlyph color\n"]
        filteredGlyphList = [gName for gName in glyphList if gName in hintedNodeDict]

        for gName in filteredGlyphList:
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
            if not templateT1RBglyph.isCompatible(targetT1RBglyph, False):
                # (NOTE: This method doesn't catch the case in which node indexes have rotated)
                print "DEFINITELY NOT COMPATIBLE: %s. Skipping..." % gName
                continue

            # Verify glyph compatibility by comparing the length of segments:
            # Create dictionaries of the coodinates of on-curve points:
            ptDict1 = getGlyphOncurveCoords(templateT1RBglyph)
            ptDict2 = getGlyphOncurveCoords(targetT1RBglyph)
            # Define segments using the point coordinates from ptDict1 and ptDict2:
            segmentsList = getSegmentsList(ptDict1, ptDict2)

            if not segmentsList:
                print "DEFINITELY NOT COMPATIBLE (contour mismatch): %s. Skipping ..." % gName
                continue

            # Get all pair combinations of those segments:
            segmentCombinationsList = list(itertools.combinations(segmentsList, 2))
            # Iterate through the segment combinations and stop as soon
            # as an intersection between two segments is found:
            for combination in segmentCombinationsList:
                seg1, seg2 = combination[0], combination[1]
                if segmentsIntersect(seg1, seg2):
                    print "POSSIBLY NOT COMPATIBLE: %s. Please check ..." % gName
                    gMark = 25 # orange
                    break # one incompatibility was found; no need to report it more than once

            # This dictionary is indexed by the combination of
            # the coordinates of each node of the current glyph:
            ttGlyphNodeIndexDict = collectTTnodeIndexes(gName, targetTTfont)

            newHintsList = []
            gHintsString = rawHintingDict[gName]
            gHintsList = gHintsString.split(";")

            for commandString in gHintsList:
                commandList = list(eval(commandString))
                commandType = commandList[0]
                if len(commandList):

                    if commandType in deltas:
                        continue

                    elif commandType in alignments:
                        nodes = [commandList[1]]
                        convertedNodes = getNewTTindexes(glyph, nodes, ttGlyphNodeIndexDict, hintedNodeDict)
                        if convertedNodes != None:
                            writeLine = True
                            targetNodeIndexList, targetNodeCoordsList = convertedNodes
                            hintParamsList = [commandList[-1]]
                        else:
                            writeLine = False
                            break

                    elif commandType in links:
                        nodes = commandList[1:3]
                        convertedNodes = getNewTTindexes(glyph, nodes, ttGlyphNodeIndexDict, hintedNodeDict)
                        if convertedNodes != None:
                            writeLine = True
                            targetNodeIndexList, targetNodeCoordsList = convertedNodes
                            hintParamsList = commandList[3:]
                        else:
                            writeLine = False
                            break

                    elif commandType in interpolations:
                        nodes = commandList[1:-1]
                        convertedNodes = getNewTTindexes(glyph, nodes, ttGlyphNodeIndexDict, hintedNodeDict)
                        if convertedNodes != None:
                            writeLine = True
                            targetNodeIndexList, targetNodeCoordsList = convertedNodes
                            hintParamsList = [commandList[-1]]
                        else:
                            writeLine = False
                            break

                if writeLine:
                    if writeCoordinates:
                        targetNodeList = targetNodeCoordsList
                    else:
                        targetNodeList = targetNodeIndexList

                    newCommandList = [commandType] + targetNodeList + hintParamsList
                    newCommandString = ','.join(map(str, newCommandList))

                    newHintsList.append(newCommandString.replace(" ", ""))

            if writeLine:
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
    'Runs the `type1` command on a font.txt file to generate a temporary PFA.'

    command = 'type1 "%s" > "%s"' % (txtFilePath, pfaFilePath)

    # Run type1 tool
    if MAC:
        pp = os.popen(command)
        report = pp.read()
        pp.close()
    if PC:
        pp = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
        out, err = pp.communicate()
        if err:
            print out, err


def makePFAfromUFO(ufoFilePath, pfaFilePath, glyphList=None):
    'Runs the `tx` command on a UFO file to generate a temporary PFA.'

    if glyphList:
        command = 'tx -t1 -g %s "%s" > "%s"' % (','.join(glyphList), ufoFilePath, pfaFilePath)
    else:
        command = 'tx -t1 "%s" > "%s"' % (ufoFilePath, pfaFilePath)

        # The order of the quotes above is extremely important.
        # Windows will understand "File with spaces" but not 'File with spaces'.

    # Run tx tool
    if MAC:
        pp = os.popen(command)
        report = pp.read()
        pp.close()
    if PC:
        pp = Popen(command, shell=True, stdout=PIPE, stderr=PIPE)
        out, err = pp.communicate()
        if err:
            print out, err


def run(writeCoordinates=False):

    # Get the folder that contains the source hinting data, and source font files:
    templateFolderPath = fl.GetPathName("Select directory that contains the 'tthints' template file...")
    if not templateFolderPath:
        'Cancel was clicked or ESC was pressed'
        return

    tthintsFilePath = os.path.join(templateFolderPath, kTTHintsFileName)

    # Verify that the files tthints, font.pfa/ufo and font.ttf exist in the folder provided:
    if not os.path.exists(tthintsFilePath):
        print "ERROR: Could not find %s file." % kTTHintsFileName
        return

    # Check if any of the possible template fonts exists -- PFA, TXT, or UFO:
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
        print "ERROR: Could not find any of the following font files: %s, %s or %s." % \
            (kPFAFileName, kTXTFileName, kUFOFileName)
        return

    # Check if font.ttf exists in source folder:
    ttfFilePath = os.path.join(templateFolderPath, kTTFFileName)
    if not os.path.exists(ttfFilePath):
        print "ERROR: Could not find %s file." % kTTFFileName
        return

    # Get the (root) folder containingt the target font files:
    baseFolderPath = fl.GetPathName("Select top directory that contains the fonts to process ...")
    if not baseFolderPath:
        'Cancel was clicked or ESC key was pressed'
        return

    startTime = time.time()

    # Create a list of glyphs that have been hinted so it can be used as a filter.
    # The rawHintingDict contains a string of raw hinting data for each glyph:
    glyphList, rawHintingDict = readTTHintsFile(tthintsFilePath)
    folderPathsList = getFolderPaths(baseFolderPath, templateFolderPath)

    if len(folderPathsList):
        delete_temporary_template_PFA = False
        print "Processing template files..."
        fl.Open(ttfFilePath)
        templateTTfont = fl[fl.ifont]
        if not os.path.exists(pfaFilePath) and os.path.exists(txtFilePath):
            delete_temporary_template_PFA = True
            makePFAfromTXT(txtFilePath, pfaFilePath)
        elif not os.path.exists(pfaFilePath) and os.path.exists(ufoFilePath):
            delete_temporary_template_PFA = True
            makePFAfromUFO(ufoFilePath, pfaFilePath, glyphList)
        fl.Open(pfaFilePath)
        templateT1font = fl[fl.ifont]

        # Make a Robofab font of the Type1 template font. This RB font is made
        # by copying each glyph. There does not seem to be a simpler method
        # that produces reliable results -- the challenge comes from having
        # to close the FL font downstream.
        templateT1RBfont = RFont()
        currentT1RBfont = CurrentFont()

        for gName in glyphList:
            g = currentT1RBfont[gName]
            templateT1RBfont.insertGlyph(g)

        hintedNodeDict, indexOnlyRawHintingDict, okToProcessTargetFonts = collectTemplateIndexes(templateTTfont, templateT1font, glyphList, rawHintingDict)
        closeAllOpenedFonts()

        if okToProcessTargetFonts:
            processTargetFonts(folderPathsList, templateT1RBfont, hintedNodeDict, glyphList, indexOnlyRawHintingDict, writeCoordinates)
        else:
            print "Can't process target fonts because of hinting errors found in template font."

        if delete_temporary_template_PFA:
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
    run(writeCoordinates=False)
