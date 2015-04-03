#FLM: Output PPMs
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
Output PPMs

This script will write (or overwrite) a `ppms` file in the same directory 
as the opened VFB file. This `ppms` file contains the TrueType stem values 
and the ppm values at which the pixel jumps occur. These values can later 
be edited as the `ppms` file is used as part of the conversion process.

==================================================
Versions:

v1.0 - Mar 27 2015 - First public release.

"""

import os
from FL import fl

kPPMsFileName = "ppms"


def collectPPMs():
	ppmsList = ["#Name\tWidth\tppm2\tppm3\tppm4\tppm5\tppm6\n"]
	for x in fl.font.ttinfo.hstem_data:
		hstem = '%s\t%d\t%d\t%d\t%d\t%d\t%d\n' % (
			x.name, x.width, x.ppm2, x.ppm3, x.ppm4, x.ppm5, x.ppm6)
		ppmsList.append(hstem)

	for y in fl.font.ttinfo.vstem_data:
		vstem = '%s\t%d\t%d\t%d\t%d\t%d\t%d\n' % (
			y.name, y.width, y.ppm2, y.ppm3, y.ppm4, y.ppm5, y.ppm6)
		ppmsList.append(vstem)

	return ppmsList


def writePPMsFile(content):
	# path to the folder where the font is contained and the font's file name:
	folderPath, fontFileName = os.path.split(fl.font.file_name)
	filePath = os.path.join(folderPath, kPPMsFileName)
	outfile = open(filePath, 'w')
	outfile.writelines(content)
	outfile.close()


def run():
	if len(fl):
		if (fl.font.file_name is None):
			print "ERROR: You must save the VFB first."
			return

		if len(fl.font.ttinfo.hstem_data):
			ppmsList = collectPPMs()
			writePPMsFile(ppmsList)
			print "Done!"
		else:
			print "ERROR: The font has no TT stems data."

	else:
		print "ERROR: No font opened."
	

if __name__ == "__main__":
	run()
