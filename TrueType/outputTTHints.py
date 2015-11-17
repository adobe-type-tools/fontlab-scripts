#FLM: Output TrueType Hints
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
Output TrueType Hints

This FontLab macro will write a simple text file `tthints` which contains
TrueType instructions and point indexes for each selected glyph.
If the external file already exists, the script will replace the existing
entries and add new entries as needed.

The script will emit an error if there are hints attached to off-curve
points, but will still write those hints. If hints are attached to nonexistent
points, the given glyph will not be written to the output file.

Example output:
n	5,13,14,1;5,22,0,1;1,9,0;1,2,0;2,0,0;2,14,0;14,4,9,0,0;4,9,18,0,-1;14,21,18,0,0
o	5,33,5,0;5,13,23,0;1,10,0;2,0,0;4,0,18,0,-1;4,10,28,0,-1


==================================================
Versions:

v1.5 - Nov 16 2015 - Do not write empty output data to tthints file
					 (A bug which affected glyphs in which a nonexistent point
					 was hinted. Reading those files made the reader choke.)
v1.4 - Apr 17 2015 - Always write to a file named 'tthints' (even if the
					 data uses point coordinates instead of point indexes).
v1.3 - Mar 25 2015 - Allow optional coordinate output.
					 Allow hinting sidebearings.
v1.2 - Mar 23 2015 – Allow instructions in x-direction.
v1.1 - Mar 04 2015 – Change name to Output TrueType Hints to supersede
					 the old script of the same name.
v1.0 - Nov 27 2013 - Initial release
"""

import os
from FL import *

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


def writeTTHintsFile(content, filePath):
	outfile = open(filePath, 'w')
	outfile.writelines(content)
	outfile.close()


def processTTHintsFileData(ttHintsList):
	storedGlyphs = []
	ttHintsDict = {}

	for item in ttHintsList:
		hintItems = item.split("\t")

		if len(hintItems) not in [2,3]:
			print "\tERROR: This hint definition does not have the correct format\n\t%s" % item
			continue

		gName = hintItems[0]
		ttHintsDict[gName] = item
		storedGlyphs.append(gName)

	return storedGlyphs, ttHintsDict


def analyzePoint(glyph, nodeIndex):
	'''Analyzes a given point for a given glyph.
	   In a normal case, this function returns a tuple of point index and point coordinates.
	   If the sidebearings have been hinted, this function returns a tuple containing the flag
	   for the appropriate sidebearing.

	'''

	point = glyph[nodeIndex]
	try: point.type

	except:
		''' This happens if left or right bottom point have been hinted.
			In the hinting code, those points are stored as point indices
			greater than the actual point count of the glyph.
			Since those points cannot be grasped in the context of the outline,
			flags are created:

			"BL" is bottom left
			"BR" is bottom right.

			Those flags are written into the output file as strings with quotes,
			so they can be parsed with eval() when reading the file later.
		'''

		if nodeIndex == len(glyph):
			point_flag = '"BL"'
		elif nodeIndex == len(glyph) + 1:
			point_flag = '"BR"'
		else:
			'Point not in glyph -- which should not happen, but you never know.'
			print '\tERROR: Point index problem in glyph %s' % glyph.name
			return None, None

		return point_flag, point_flag

	point_coordinates = point.x, point.y

	if point.type == nOFF:
		gName = glyph.name
		print "\tWARNING: Off-curve point %s hinted in glyph %s." % (point_coordinates, gName)

	return nodeIndex, point_coordinates


def collectInstructions(tth, glyph, coord_option):
	''' Parses tth commands (list of integers) and returns them formatted
		for writing the data into an external text file.


		tth data structure:
		-------------------

		alignment points:
		[command code, point index, alignment]

		single and double links:
		[command code, point index 1, point index 2, stem ID, alignment]

		interpolations:
		[command code, point index 1, point index 2, point index 3, alignment]

		deltas:
		[command code, point index, offset, point range min, point range max]
	'''

	coord_commandsList = []
	index_commandsList = []

	for inst in tth.commands:
		command = [inst.code]
		coord_command = [inst.code]
		index_command = [inst.code]

		for p in inst.params:
			'create raw tth command list to parse'
			command.append(p)

		if inst.code in deltas:
			'delta'
			nodeIndex = command[1]
			deltaDetails = command[2:]
			point_index, point_coordinates = analyzePoint(glyph, nodeIndex)

			coord_command.append(point_coordinates)
			index_command.append(point_index)
			coord_command.extend(deltaDetails)
			index_command.extend(deltaDetails)

		elif inst.code in links:
			'single- or double link'
			linkDetails = command[3:]
			for nodeIndex in command[1:3]:
				point_index, point_coordinates = analyzePoint(glyph, nodeIndex)

				coord_command.append(point_coordinates)
				index_command.append(point_index)
			coord_command.extend(linkDetails)
			index_command.extend(linkDetails)

		elif inst.code in alignments + interpolations:
			'alignment or interpolation'
			alignmentDetails = command[-1]
			for nodeIndex in command[1:-1]:
				point_index, point_coordinates = analyzePoint(glyph, nodeIndex)

				coord_command.append(point_coordinates)
				index_command.append(point_index)
			coord_command.append(alignmentDetails)
			index_command.append(alignmentDetails)

		else:
			'unknown instruction code'
			print "\tERROR: Hinting problem in glyph %s." % glyph.name
			coord_command = []
			index_command = []

		if None in coord_command:
			' hinting error has been picked up by anyalyzePoint()'
			return []

		coord_command_string = ','.join(map(str, coord_command))
		coord_command_string = coord_command_string.replace(' ', '')
		index_command_string = ','.join(map(str, index_command))

		index_commandsList.append(index_command_string)
		coord_commandsList.append(coord_command_string)

	if coord_option:
		return coord_commandsList
	else:
		return index_commandsList


def processGlyphs(selectedGlyphs, storedGlyphs, ttHintsDict, coord_option):
	# Iterate through all the glyphs instead of just the ones selected.
	# This way the order of the items in the output file will be constant and predictable.

	allGlyphsHintList = ["# Glyph name\tTT hints\n"]

	for glyph in fl.font.glyphs:
		gName = glyph.name

		if (gName in selectedGlyphs) or (gName in storedGlyphs):
			if gName in selectedGlyphs:
				# If the glyph is selected, read its hints.
				tth = TTH(glyph)
				tth.LoadProgram()

				if len(tth.commands):
					instructionsList = collectInstructions(tth, glyph, coord_option)
					if len(instructionsList):
						gHints = "%s\t%s\n" % (gName, ';'.join(instructionsList))
						allGlyphsHintList.append(gHints)
				else:
					print "WARNING: The glyph %s has no TrueType hints." % gName
			else:
				# If the glyph is not selected but present in the external
				# file, just read the data from the ttHintsDict and dump it.
				allGlyphsHintList.append(ttHintsDict[gName] + '\n')

	return allGlyphsHintList


def run(font, parentDir, coord_option):
	kTTHintsFileName = "tthints"

	tthintsFilePath = os.path.join(parentDir, kTTHintsFileName)
	selectedGlyphs = [font[gIndex].name for gIndex in range(len(font)) if fl.Selected(gIndex)]

	if not len(selectedGlyphs):
		print "Select the glyph(s) to process and try again."
		return

	if os.path.exists(tthintsFilePath):
		print "WARNING: The %s file at %s will be modified." % (kTTHintsFileName, tthintsFilePath)
		ttHintsList = readTTHintsFile(tthintsFilePath)
		modFile = True
	else:
		ttHintsList = []
		modFile = False

	if len(ttHintsList):
		storedGlyphs = processTTHintsFileData(ttHintsList)[0]
		ttHintsDict = processTTHintsFileData(ttHintsList)[1]
	else:
		storedGlyphs = []
		ttHintsDict = {}

	allGlyphsHintList = processGlyphs(selectedGlyphs, storedGlyphs, ttHintsDict, coord_option)

	if len(allGlyphsHintList) > 1:
		writeTTHintsFile(allGlyphsHintList, tthintsFilePath)
	else:
		print "The script found no TrueType hints to output."
		return

	if not modFile:
		print "File %s was saved at %s" % (kTTHintsFileName, tthintsFilePath)

	print "Done!"


def preRun(coord_option=False):
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

	run(font, parentDir, coord_option)


if __name__ == "__main__":
	preRun()
