#FLM: Input TrueType Hints

__copyright__ = __license__ =  """
Copyright (c) 2013 Adobe Systems Incorporated. All rights reserved.
 
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
Input TrueType Hints v1.1 - Sep 07 2013

This FontLab macro will read an external simple text file containing
TrueType instructions for each glyph, and will apply that data to the
glyphs. The hints can be further edited and written out using the macro
named "Output TrueType Hints".

==================================================
Versions:
v1.0 - Jan 07 2013 - Initial release
v1.1 - Sep 07 2013 - Enabled the reading of 'tthints' files with an optional column for glyph color mark
"""

#----------------------------------------

kTTHintsFileName = "tthints"
debugMode = False

#----------------------------------------

kAlignLinkTop = 1
kAlignLinkBottom = 2
kAlignLinkNearY = 8
kSingleLinkY = 4
kDoubleLinkY = 6
kInterpolateLink = 14

k1NodeIndexList = [kAlignLinkTop, kAlignLinkBottom, kAlignLinkNearY]
k2NodeIndexList = [kSingleLinkY, kDoubleLinkY]
k3NodeIndexList = [kInterpolateLink]

#----------------------------------------

import os


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


def applyTTHints(ttHintsList):
	glyphsHinted = 0
	for item in ttHintsList:
		hintItems = item.split("\t")
		
		if len(hintItems) == 3:
			gName, gHints, gMark = hintItems
			gMark = int(gMark)
		elif len(hintItems) == 2:
			gName, gHints = hintItems
			gMark = 80 # Green color
		else:
			print "ERROR: This hint definition does not have the correct format\n\t%s" % item
			continue

		gIndex = fl.font.FindGlyph(gName)
		
		if gIndex != -1:
			glyph = fl.font[gName]
		else:
			print "ERROR: Glyph %s not found in the font." % gName
			continue
		
		if not len(gHints.strip()):
			print "WARNING: There are no hints defined for glyph %s." % gName
			continue

		gHintsList = gHints.split(";")
		
		tth = TTH(glyph)
		tth.LoadProgram(glyph)
		tth.ResetProgram()
		
		if debugMode:
			print gName
		
		for item in gHintsList:
			itemList = item.split(",")
			
			if len(itemList) < 3:
				print "ERROR: A hint definition for glyph %s does not have enough parameters: %s" % (gName, item)
				continue
			
			try:
				commandType = int(itemList[0])
			except:
				print "ERROR: A hint definition for glyph %s has an invalid command type: %s" % (gName, item)
				continue
			
			# Create the TTHCommand
			try:
				ttc = TTHCommand(commandType)
			except RuntimeError:
				print "ERROR: A hint definition for glyph %s has an invalid command type: %s\n\t\tThe first value must be within the range 1-23." % (gName, item)
				continue
			
			# Remove the first item of the list (i.e. the command type)
			del(itemList[0])
			
			# Determine how many parameters to consider as node indexes
			if commandType in k1NodeIndexList: # the instruction is an Align Link (top or bottom), so only one node is provided
				nodeIndexCount = 1
			elif commandType in k2NodeIndexList: # the instruction is a Single Link or a Double Link, so two nodes are provided
				nodeIndexCount = 2
			elif commandType in k3NodeIndexList: # the instruction is an Interpolation Link, so three nodes are provided
				nodeIndexCount = 3
			else:
				print "WARNING: Hint type %d in glyph %s is not yet supported." % (commandType, gName)
				nodeIndexCount = 0
			
			paramError = False
			
			# Use the remaining items for setting the parameters, one by one
			for i in range(len(itemList)):
				try:
					paramValue = int(itemList[i])
					if nodeIndexCount:
						gNode = glyph.nodes[paramValue]
				except IndexError:
					print "ERROR: A hint definition for glyph %s is referencing an invalid node index: %s" % (gName, item)
					paramError = True
					break
				except:
					print "ERROR: A hint definition for glyph %s has an invalid parameter value: %s" % (gName, item)
					paramError = True
					break
				ttc.params[i] = paramValue
				nodeIndexCount -= 1
			
			if not paramError:
				tth.commands.append(ttc)
		
		if len(tth.commands):
			tth.SaveProgram(glyph)
			glyph.mark = gMark
			fl.UpdateGlyph(gIndex)
			glyphsHinted += 1
	
	if glyphsHinted > 0:
		fl.font.modified = 1


def run(parentDir):
	tthintsFilePath = os.path.join(parentDir, kTTHintsFileName)
	if os.path.exists(tthintsFilePath):
		ttHintsList = readTTHintsFile(tthintsFilePath)
	else:
		print "Could not find the %s file at %s" % (kTTHintsFileName, tthintsFilePath)
		return
	
	if len(ttHintsList):
		applyTTHints(ttHintsList)
		print "Done!"
	else:
		print "The %s file at %s has no hinting data." % (kTTHintsFileName, tthintsFilePath)
		return
		

def preRun():
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
	
	run(parentDir)


if __name__ == "__main__":
	preRun()
