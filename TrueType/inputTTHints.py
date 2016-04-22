#FLM: Input TrueType Hints
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
Input TrueType Hints

This FontLab macro will read an external simple text file `tthints` containing
TrueType instructions and hinted point indexes or point coordinates for a number
of glyphs, and will apply this data to the glyphs of an open VFB.

==================================================
Versions:

v1.4 - Apr 17 2015 - Remove unneeded coord_option, now that hints expressed with
					 point coordinates are saved as 'tthints' instead of 'tthints_coords'.
v1.3 - Mar 24 2015 - Enable reading 'tthints_coords' file with coordinates.
v1.2 - Mar 23 2015 - Enable instructions in x-direction.
v1.1 - Sep 07 2013 - Enable the reading of 'tthints' files with an optional
					 column for glyph color mark.
v1.0 - Jan 07 2013 - Initial release.
"""

#----------------------------------------

debugMode = False

#----------------------------------------

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

#----------------------------------------
fuzziness = 2
# Defines area to search for a point that might have moved in TT transformation.
# 0 =  1 possibility (the exact point coordinates)
# 1 =  9 possibilities (1 step in each direction from original point)
# 2 = 25 possibilities (2 steps in each direction)
# 3 = 49 possibilities (3 steps in each direction) etc.

pointErrors = {}
fuzzyPoints = {}
#----------------------------------------

import os
from FL import *
import itertools

def readTTHintsFile(filePath):
	file = open(filePath, "r")
	data = file.read()
	file.close()
	lines = data.splitlines()

	ttHintsList = []

	for i in range(len(lines)):
		line = lines[i]
		# Skip over blank lines
		stripline = line.strip()
		if not stripline:
			continue
		# Skip over comments
		if line.find('#') >= 0:
			continue
		else:
			ttHintsList.append(line)

	return ttHintsList


def findFuzzyPoint(glyphName, point, pointDict, fuzziness):
	'''
	Finds points that fall inside a fuzzy area around
	the original coordinate. If only one point is found
	in that area, the point index will be returned.
	Otherwise returns None.

	Solves off-by-one issues.
	'''

	fuzzyX = range(point[0]-fuzziness, point[0]+fuzziness+1,)
	fuzzyY = range(point[1]-fuzziness, point[1]+fuzziness+1,)
	possibleFuzzyPoints = [fuzzyCoords for fuzzyCoords in itertools.product(fuzzyX, fuzzyY)]
	allPoints = pointDict.keys()
	overlap = set(allPoints) & set(possibleFuzzyPoints)

	if len(overlap) == 1:
		# make sure that only one point is found within the fuzzy area
		oldPoint = list(overlap)[0]
		pointIndex = pointDict[oldPoint]
		fuzzyPoints.setdefault(glyphName, [])
		if not (oldPoint, point) in fuzzyPoints[glyphName]:
			print '\tINFO: In glyph {}, point #{} has changed from {} to {}.'.format(glyphName, pointIndex, oldPoint, point)
			fuzzyPoints[glyphName].append((oldPoint, point))

		return pointIndex
	else:
		return None


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
				# Try fuzziness if no exact coordinate match is found:
				fuzzyPointIndex = findFuzzyPoint(glyph.name, item, pointDict, fuzziness)
				if fuzzyPointIndex != None:
					pointIndex = fuzzyPointIndex
				else:
					pointErrors.setdefault(glyph.name, [])
					if not item in pointErrors[glyph.name]:
						print '\tERROR: point %s does not exist in glyph %s.' % (item, glyph.name)
						pointErrors[glyph.name].append(item)

			output.append(pointIndex)
		else:
			'other hinting data, integers'
			output.append(item)

	if None in output:
		# a point was not found at all, so no hinting recipe is returned
		return []
	else:
		return output


def applyTTHints(ttHintsList):
	glyphsHinted = 0
	for line in ttHintsList:
		hintItems = line.split("\t")

		if len(hintItems) == 3:
			'line contains glyph name, hint info and mark color'
			pass

		elif len(hintItems) == 2:
			'line does not contain mark color'
			hintItems.append(80) # green

		else:
			print "ERROR: This hint definition does not have the correct format\n\t%s" % line
			continue

		gName, gHintsString, gMark = hintItems
		gIndex = fl.font.FindGlyph(gName)

		if gIndex != -1:
			glyph = fl.font[gName]
		else:
			print "ERROR: Glyph %s not found in the font." % gName
			continue

		if not len(gHintsString.strip()):
			print "WARNING: There are no hints defined for glyph %s." % gName
			continue

		gHintsList = gHintsString.split(";")

		tth = TTH(glyph)
		tth.LoadProgram(glyph)
		tth.ResetProgram()

		if debugMode:
			print gName

		readingError = False
		for commandString in gHintsList:
			raw_commandList = list(eval(commandString))

			commandType = raw_commandList[0]
			commandList = transformCommandList(glyph, raw_commandList)

			if not commandList:
				readingError = True
				continue

			if len(commandList) < 3:
				print "ERROR: A hint definition for glyph %s does not have enough parameters: %s" % (gName, commandString)
				continue

			# Create the TTHCommand
			try:
				ttc = TTHCommand(commandType)
			except RuntimeError:
				print "ERROR: A hint definition for glyph %s has an invalid command type: %s\n\t\tThe first value must be within the range %s-%s." % (gName, commandType, vAlignLinkTop, vFinDelta)
				continue


			paramError = False

			if commandType in deltas:
				nodes = [commandList[1]]
			elif commandType in links:
				nodes = commandList[1:3]
			elif commandType in alignments + interpolations:
				nodes = commandList[1:-1]
			else:
				print "WARNING: Hint type %d in glyph %s is not supported." % (commandType, gName)
				paramError = True
				nodes = []

			for nodeIndex in nodes:
				try:
					gNode = glyph.nodes[nodeIndex]
				except IndexError:
					if nodeIndex in range(len(glyph), len(glyph)+2):
						pass
					else:
						print "ERROR: A hint definition for glyph %s is referencing an invalid node index: %s" % (gName, nodeIndex)
						paramError = True
						break


			for i, item in enumerate(commandList[1:]):
				ttc.params[i] = item

			if not paramError:
				tth.commands.append(ttc)

		if readingError:
			print '\tProblems with reading hinting recipe of glyph %s\n' % (gName)

		if len(tth.commands):
			tth.SaveProgram(glyph)
			if readingError:
				glyph.mark = 12
			else:
				glyph.mark = int(gMark)
			fl.UpdateGlyph(gIndex)
			glyphsHinted += 1

	if glyphsHinted > 0:
		fl.font.modified = 1


def run(parentDir):
	kTTHintsFileName = "tthints"

	tthintsFilePath = os.path.join(parentDir, kTTHintsFileName)
	if os.path.exists(tthintsFilePath):
		print 'Reading', tthintsFilePath
		ttHintsList = readTTHintsFile(tthintsFilePath)
	else:
		print "Could not find the %s file at %s" % (kTTHintsFileName, tthintsFilePath)
		return

	if len(ttHintsList):
		applyTTHints(ttHintsList)
		print "TT hints added."
	else:
		print "The %s file at %s has no hinting data." % (kTTHintsFileName, tthintsFilePath)
		return



def preRun():
	# Clear the Output window
	fl.output = '\n'

	if fl.count == 0:
		print "Open a font first."
		return

	font = fl.font

	if len(font) == 0:
		print "The font has no glyphs."
		return

	try:
		parentDir = os.path.dirname(os.path.realpath(font.file_name))
	except AttributeError:
		print "The font has not been saved. Please save the font and try again."
		return

	run(parentDir)


if __name__ == "__main__":
	preRun()
