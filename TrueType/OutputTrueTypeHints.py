#FLM: Output TrueType Hints
# coding: utf-8

__copyright__ = __license__ =  """
Copyright (c) 2013, 2015 Adobe Systems Incorporated. All rights reserved.
 
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

__doc__ = """
Output TrueType Hints v1.3 - Mar 25 2015

This FontLab macro will write an external simple text file containing
TrueType instructions for each selected glyph. If the external file
already exists, the script will replace the existing entries and add
new ones. The hinting data can be loaded back into the font by using
the macro named "Input TrueType Hints".

The script will emit an error if there are hints attached to off-curve
points. That's the only difference from OutputTrueTypeHints.py.

==================================================
Versions:
v1.3 - Mar 25 2015 - Allow coordinate output 
v1.2 - Mar 23 2015 – Allow instructions in x-direction.
v1.1 - Mar 04 2015 – change name to Output TrueType Hints to supersede 
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
anchors = [vAlignLinkTop, vAlignLinkNear, vAlignLinkBottom, hAlignLinkNear]


listGlyphsSelected = []
def getgselectedglyphs(font, glyph, gindex):
	listGlyphsSelected.append(glyph.name)
fl.ForSelected(getgselectedglyphs)


allGlyphsHintList = ["# Glyph name\tTT hints\n"]


def readTTHintsFile(filePath):
	file = open(filePath, "r")
	data = file.read()
	file.close()
	lines = data.splitlines()

	ttHintsList = []
	
	for i in range(len(lines)):
		line = lines[i]
		# Skip over blank lines
		line2 = line.strip()
		if not line2:
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


ttHintsGlyphNamesList = []
def processTTHintsFileData(ttHintsList):
	ttHintsDict = {}
	
	for item in ttHintsList:
		hintItems = item.split("\t")
		
		if len(hintItems) != 2:
			print "\tERROR: This hint definition does not have the correct format\n\t%s" % item
			continue
		
		gName = hintItems[0]
		ttHintsDict[gName] = item
		ttHintsGlyphNamesList.append(gName)
	
	return ttHintsDict
	

def checkForOffCurve(commands, gName):
	gIndex = fl.font.FindGlyph(gName)
	commandCode = commands[0]
	
	if commandCode in anchors: 
		'The instruction is an Align Link (top or bottom), so only one node index is provided.'
		nodeIndexList = [commands[1]]
	elif commandCode in links: 
		'The instruction is a Single Link or a Double Link, so two node indexes are provided.'
		nodeIndexList = [x for x in commands[1:3]]
	elif commandCode in interpolations: 
		'The instruction is an Interpolation Link, so three node indexes are provided.'
		nodeIndexList = [x for x in commands[1:4]]
	elif commandCode in deltas:
		'The instruction is a Delta, one node index is provided.'
		nodeIndexList = [commands[1]]
	else:
		print "ERROR: Hint type not supported in %s." % gName
		nodeIndexList = []
	
	for hintedNodeIndex in nodeIndexList:
		node = fl.font[gIndex][hintedNodeIndex]
		try:
			node.type
		except:
			print "ERROR: Hinting problem in glyph %s." % gName
			continue

		if node.type == nOFF:
			print "ERROR: Hinted off-curve point #%d in glyph %s." % (hintedNodeIndex, gName)


def collectInstructions(tth, gName):
	commandsList = []
	for inst in tth.commands:
		command = [inst.code]
		for p in inst.params:
			command.append(p)

		command_string = ','.join(map(str, command))
		# Convert list of instructions to comma-separated string.
		commandsList.append(command_string)
		
		checkForOffCurve(command, gName)
	return commandsList


def analyzePoint(glyph, nodeIndex):
	point = glyph[nodeIndex]
	try: point.type

	except:
		'''
		Left or right bottom point have been hinted:
		In the hinting code, those points are stored as point indices larger than the actual glyph.
		Since those points cannot be grasped in the context of an outline, 
		flags are created

		'''
		if nodeIndex == len(glyph):
			point_flag = '"BL"'
		elif nodeIndex == len(glyph) + 1:
			point_flag = '"BR"'
		else:
			'point not in glyph'
			print '\tERROR: Hinting problem in glyph %s' % glyph.name
			continue

		return point_flag

	point_coordinates = point.x, point.y

	if point.type == nOFF:
		gName = glyph.name
		print "\tERROR: Off-curve point %s hinted in glyph %s." % (point_coordinates, gName)

	return point_coordinates



def collectInstructions2(tth, gName, coord_option):
	'''

	Data structure: 

	anchors:
	[command code, point index, alignment]

	single and double links:
	[command code, point index 1, point index 2, stem ID, alignment]

	interpolations:
	[command code, point index 1, point index 2, point index 3, alignment]

	deltas:
	[command code, point index, offset, point range min, point range max]

	'''

	glyph = fl.font[gName]
	coord_commandsList = []
	commandsList = []
	for inst in tth.commands:
		command = [inst.code]
		coord_command = [inst.code]

		for p in inst.params:
			command.append(p)


		if inst.code in deltas:
			'delta'
			nodeIndex = command[1]
			deltaDetails = command[2:]
			point_coordinates = analyzePoint(glyph, nodeIndex)

			coord_command.append(point_coordinates)
			coord_command.extend(deltaDetails)

		elif inst.code in links:
			'single- or double link'

			for nodeIndex in command[1:3]:
				point_coordinates = analyzePoint(glyph, nodeIndex)

				coord_command.append(point_coordinates)
			coord_command.extend(command[-2:])

		elif inst.code in anchors + interpolations:
			'anchor or interpolation'
			for nodeIndex in command[1:-1]:
				point_coordinates = analyzePoint(glyph, nodeIndex)

				coord_command.append(point_coordinates)
			coord_command.append(command[-1])

		else:
			'unknown instruction code'
			print "\tERROR: Hinting problem in glyph %s." % gName
			continue


		coord_command_string = ','.join(map(str, coord_command))
		coord_command_string = coord_command_string.replace(' ', '')
		command_string = ','.join(map(str, command))

		commandsList.append(command_string)
		coord_commandsList.append(coord_command_string)

	if coord_option:
		return coord_commandsList
	else:
		return commandsList


def processGlyphs(ttHintsDict, coord_option):
	# Iterate through all the glyphs instead of just the ones selected.
	# This way the order of the items in the output file will be constant and predictable.
	for glyph in fl.font.glyphs:
		gName = glyph.name
		
		if (gName in listGlyphsSelected) or (gName in ttHintsGlyphNamesList):
			if gName in listGlyphsSelected:
				tth = TTH(glyph)
				tth.LoadProgram()
		
				if len(tth.commands):
					gHints = "%s\t%s\n" % (gName, ';'.join(collectInstructions2(tth, gName, coord_option)))
					allGlyphsHintList.append(gHints)
				else:
					print "WARNING: The glyph %s has no TrueType hints." % gName
			else:
				allGlyphsHintList.append(ttHintsDict[gName] + '\n')


def run(parentDir, coord_option):

	if coord_option:
		kTTHintsFileName = "tthints_coords"
	else:
		kTTHintsFileName = "tthints"


	tthintsFilePath = os.path.join(parentDir, kTTHintsFileName)
	
	if not len(listGlyphsSelected):
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
		ttHintsDict = processTTHintsFileData(ttHintsList)
	else:
		ttHintsDict = {}
	
	processGlyphs(ttHintsDict, coord_option)
	
	if len(allGlyphsHintList) > 1:
		writeTTHintsFile(allGlyphsHintList, tthintsFilePath)
	else:
		print "The script found no TrueType hints to output."
		return

	if not modFile:
		print "File %s was saved at %s" % (kTTHintsFileName, tthintsFilePath)
	
	print "Done!"
		

def preRun(coord_option=False):
	# Reset the Output window
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
	
	run(parentDir, coord_option)


if __name__ == "__main__":
	preRun()
