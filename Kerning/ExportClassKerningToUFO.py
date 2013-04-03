#FLM: Export FontLab class kerning to UFO
import os
moduleFound = False

try:
    from kernExport import *
    reload(kernExport)
    moduleFound = True

except ImportError:
    modulePath = os.path.join(fl.userpath, 'Macros', 'System', 'Modules')
    url = 'https://github.com/adobe-type-tools/python-modules'
    print '''

    Please make sure you have placed the "kernExport.py" module in your Macros/System/Modules folder:
    %s
    Get the module here:
    %s 

    ''' % (modulePath, url)


if moduleFound:

    # three options are possible; for further details see kernExport.__doc__:
    # kernExport.ClassKerningToUFO(fl.font, prefixOption = 'MM')   # prefix kerning classes in MetricsMachine-style
    # kernExport.ClassKerningToUFO(fl.font, prefixOption = 'UFO3') # prefix kerning classes in UFO3-style
    # kernExport.ClassKerningToUFO(fl.font)                        # do not change the name of kerning classes (apart from side markers)

    kernExport.ClassKerningToUFO(fl.font, 'MM')
