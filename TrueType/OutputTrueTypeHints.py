#FLM: Output TrueType Hints

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
Output TrueType Hints v1.0 - Jan 07 2013

This FontLab macro will write an external simple text file containing
TrueType instructions for each selected glyph. If the external file
already exists, the script will replace the existing entries and add
new ones. The hinting data can be loaded back into the font by using
the macro named "Input TrueType Hints".

==================================================
Versions:
v1.0 - Jan 07 2013 - Initial release
"""

#----------------------------------------

kTTHintsFileName = "tthints"

#----------------------------------------

import os


listGlyphsSelected = []
def getgselectedglyphs(font, glyph, gindex):
	listGlyphsSelected.append(glyph.name)
fl.ForSelected(getgselectedglyphs)


allGlyphsHintList = ["#Glyph name\tTT hints\n"]


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
			print "ERROR: This hint definition does not have the correct format\n\t%s" % item
			continue
		
		gName = hintItems[0]
		ttHintsDict[gName] = item
		ttHintsGlyphNamesList.append(gName)
	
	return ttHintsDict
	

def collectInstructions(tth, gName):
	commandsList = []
	for inst in tth.commands:
		params = ''
		for p in inst.params:
			params += "%d," % p
		command = "%d,%s" % (inst.code, params[:-1]) # trim last comma
		commandsList.append(command)
	return commandsList


def processGlyphs(ttHintsDict):
	# Iterate through all the glyphs instead of just the ones selected.
	# This way the order of the items in the output file will be constant and predictable.
	for glyph in fl.font.glyphs:
		gName = glyph.name
		
		if (gName in listGlyphsSelected) or (gName in ttHintsGlyphNamesList):
			if gName in listGlyphsSelected:
				tth = TTH(glyph)
				tth.LoadProgram()
		
				if len(tth.commands):
					gHints = "%s\t%s\n" % (gName, ';'.join(collectInstructions(tth, gName)))
					allGlyphsHintList.append(gHints)
				else:
					print "WARNING: The glyph %s has no TrueType hints." % gName
			else:
				allGlyphsHintList.append(ttHintsDict[gName] + '\n')


def run(parentDir):
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
	
	processGlyphs(ttHintsDict)
	
	if len(allGlyphsHintList) > 1:
		writeTTHintsFile(allGlyphsHintList, tthintsFilePath)
	else:
		print "The script found no TrueType hints to output."
		return

	if not modFile:
		print "File %s was saved at %s" % (kTTHintsFileName, tthintsFilePath)
	
	print "Done!"
		

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
