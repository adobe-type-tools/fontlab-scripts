#FLM: Export FontLab class kerning to UFO

import os
from FL import *

module_found = False
defcon_found = False

modules_urls = {
    'defcon': 'https://github.com/typesupply/defcon',
    'ufoLib': 'https://github.com/unified-font-object/ufoLib',
    'fontTools.misc.py23': 'https://github.com/fonttools/fonttools',
    'kernExport': 'https://github.com/adobe-type-tools/python-modules',
}


def print_module_msg(err):
    module_name = err.message.split()[-1]
    print('%s was found.' % err)
    print('Get it at %s' % modules_urls.get(module_name))


try:
    import defcon
    defcon_found = True

except ImportError as err:
    print_module_msg(err)
    print('')


if defcon_found:
    try:
        import kernExport
        module_found = True

    except ImportError as err:
        print_module_msg(err)
        module_path = os.path.join(fl.userpath, 'Macros', 'System', 'Modules')
        print("Then place kernExport.py file in FontLab's Modules folder at")
        print("%s" % module_path)
        print('')


def run():
    if module_found:

        # Three options are possible for kerning classes prefix:
        # 'MM': MetricsMachine-style
        # 'UFO3': UFO3-style
        # None: don't change the name of kerning classes (apart from
        #       the side markers)
        # For further details see kernExport.__doc__

        kernExport.ClassKerningToUFO(fl.font, prefixOption='MM')


if __name__ == '__main__':
    run()
