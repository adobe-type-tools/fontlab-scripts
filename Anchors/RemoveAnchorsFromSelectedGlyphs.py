#FLM: Remove Anchors From Selected Glyphs

__copyright__ = __license__ =  """
Copyright (c) 2010-2013 Adobe Systems Incorporated. All rights reserved.

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

__doc__ = """
Remove Anchors From Selected Glyphs v1.2 - Apr 10 2013

Removes the anchors on the selected glyphs.

==================================================
Versions:
v1.0   - Apr 29 2010 - Initial version.
v1.1   - Jun 15 2012 - Added undo support.
v1.2   - Apr 10 2013 - Remaned the macro from "Remove Anchors" to the current name.

"""

listGlyphsSelected = []
def getgselectedglyphs(font, glyph, gindex):
	listGlyphsSelected.append(gindex)
fl.ForSelected(getgselectedglyphs)

anchorFound = False

for gIndex in listGlyphsSelected:
	glyph = fl.font[gIndex]
	if len(glyph.anchors) > 0:
		fl.SetUndo(gIndex)
		anchorIndexList = range(len(glyph.anchors))
		anchorIndexList.reverse() # reversed() was added in Python 2.4; FL 5.0.4 is tied to Python 2.3
		for i in anchorIndexList: # delete from last to first
			del glyph.anchors[i]
		fl.UpdateGlyph(gIndex)
		anchorFound = True

if anchorFound:
	fl.font.modified = 1
	print 'Anchors removed!'
else:
	print 'No anchors found!'
