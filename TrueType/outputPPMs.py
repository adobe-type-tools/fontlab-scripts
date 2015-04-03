#FLM: Export PPMs

"""
This script will write (or overwrite) a 'ppms' file in the same directory 
as the opened VFB file. This 'ppms' file contains the TrueType stem values 
and the ppm values at which the pixel jumps occur. These values can later 
be edited as the 'ppms' file is used as part of the conversion process.
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
