#!/usr/bin/env python3
import os
import sys

from scripts.fabricate    import *
#from scripts.build_util   import *
from scripts.generators   import *
#from scripts.remote_build import *

####### BUILD TYPE
DEVELOPMENT_BUILD=False

TARGET={
    "DEVICE"    : "NXP_LPCLPC11U24FHI33_301",   # Name of device building for.
    "CPU"       : "cortex-m0",
    "CPU_OPTS"  : [ "-mcpu=cortex-m0",
                    "-mtune=cortex-m0",
                    "-mthumb",
                    "-DCORE_M0",
                    "-DINCLUDE_ROM_DIV"
                    ],

}

####### COMMON PROJECT BUILD DEFINITIONS
# Saves Redundancy in BUILD definition.


####### PROJECT BUILD DEFINITIONS
# Convention:
#    KEYS are Declared 'KEY'
#    PARAMS are Declared "PARAM"
BUILD={
    # Build Type Control
    'DEBUG_BUILD'   : [True,False], # [True] to build debug-able version.
                                    # [False] to build production version.
                                    # [True,False] to build both a debug-able and production version.

    # Binary Built Files Destination
    'BUILD_DIR'     : "build",        # Place where Binaries are placed
    'DEBUG_DIR'     : "debug_build",  # Place where Binaries are placed (debug build)

    # Define which tools are used to build which extensions
    'EXT' :   {
        'GCC'       : [".c"],
        'GXX'       : [".cpp"],
        'GAS'       : [".S"],
    },

    # The Tools we use, by architecture.
    #   'AVR' toolchain avr-gcc
    #   'TOOL' is a Command, typically a code generator, it doesn't belong to a
    #               tool chain per-se.
    #   'SCRIPT' is a Build Script.
    'TOOLS' : {
        'PATH': {
            'ARM'   : "/opt/gcc-arm-none-eabi-4_8-2014q1/bin",
            'TOOL'  : "../Tools",
            'SCRIPT': "scripts",
        },
        'GCC'      : {'ARM' : "arm-none-eabi-gcc"},
        'GXX'      : {'ARM' : "arm-none-eabi-gcc"},
        'GAS'      : {'ARM' : "arm-none-eabi-gcc"},
        'OBJ-COPY' : {'ARM' : "arm-none-eabi-objcopy"},
        'OBJ-DUMP' : {'ARM' : "arm-none-eabi-objdump"},
    }, # END TOOLS

    # The Options we pass to the Tools.
    'OPTS'  : {
        'GCC' : {
            'WARN' : [
                "-Wall",
            ],
            'ARM'       : {
                'CFLAGS' : [
                    "-std=gnu99",
                    "-nostartfiles",
                    "-ffunction-sections",
                    "-fdata-sections",
#                    "-fpack-struct",
#                    "-fno-inline-small-functions",
#                    "-fno-move-loop-invariants",
#                    "-fno-tree-scev-cprop",
                ] + TARGET['CPU_OPTS'],
                'DEBUG_CFLAGS' : [
                    "-DDEBUG",
                ],
                'LDFLAGS' : [
                    "--relax",
                    "--gc-sections",
                ],
            },
        }, # END GCC
        'GXX' : {
            'WARN' : [
                "-Wall",
                "-Wno-reorder",
            ],
            'AVR'       : {
                'CFLAGS' : [
                    "-nostartfiles",
                    "-ffunction-sections",
                    "-fdata-sections",
#                    "-fpack-struct",
#                    "-fno-inline-small-functions",
#                    "-fno-move-loop-invariants",
#                    "-fno-tree-scev-cprop",
                    "-mcpu="+TARGET['CPU'],
                    "-mtune="+TARGET['CPU'],
                ],
                'DEBUG_CFLAGS' : [
                    "-DDEBUG",
                ],
                'LDFLAGS' : [
                    "--relax",
                    "--gc-sections",
                ],
            },
        }, # END GXX
        'GAS' : {
            'WARN' : [
                "-Wall",
            ],
            'AVR'       : {
                'CFLAGS' : [
                    "-x","assembler-with-cpp",
                    "-mcpu="+TARGET['CPU'],
                    "-mtune="+TARGET['CPU'],
#                    "-DF_CPU="+str(AVR_TARGET['F_CPU']),
                ],
            },
        }, # END GAS
    }, # END OPTS

    # Targets to skip Building.  USED DURING DEVELOPMENT.
    'SKIP' : [
    ],

    # External Sources to Build/Preliminary Operations
    #  { <Name> : { Options }, ... }
    #     'VERSION'     - Displayed Version of the Module/Library
    #     'BASEDIR'     - (Optional) Specifies a Directory which contains the source if it is not "VERSION",
    #     'MAKE'        - List of commands used to "make" these external sources
    #
    #   EXTERNAL is used for:
    #       1: to build "build" tools from source
    #       2: to fetch or update externally maintained source repositories.
    #       3: To generate code files from data.
    #       4: Any other prilimary or utility pre-build function
    #           Technically autotools type configuration tests could be
    #           integrated at this point.
    #   All External builds are completed before the main build starts.
    'EXTERNAL'  : {
    },

    # Sources to Build
    #   FORMAT:
    #     { <MODULE/LIBRARY Name> : { Options }, ... }
    #   OPTIONS:
    #     'VERSION' - Displayed Version of the Module/Library
    #     'ARCH'    - The Architecture to build the Module/Library with. (Must Match 'TOOLS')
    #     'CORE'    - The CORE of the processor to build for. (Must Match OPTS[<TOOL>][<ARCH>])
    #     'PREFIX'  - Directory Library/Module is found under.
    #     'BASEDIR' - (Optional) Specifies a Directory which contains the source if it is not "VERSION",
    #     'LIBRARY' - Optional - Package as a Library, called this name.
    #     'MODULE'  - Optional - Marks a Package as a module of the main application.
    #     'APP'     - Optional - Marks a Package as the main application.
    #     'LISTING' - Optional - Generates an assembler listing of each file.  Option is passed to the assembler to control the listing.
    #     'SRC'     - List of Source Files to Build.
    #                 Each element may be a single file, or a tupple.
    #                 the single file is equivalent to a tuple (file, BUILD[BUILD_DIR], 0)
    #                 the tuple is:
    #                     (src file, dest directory, the number of path elements to strip from source to destination)
    #     'INCLUDE' - List of Include Directories specific to Building the Module/Library
    #     'USES'    - List of Modules/Libraries used by this module
    #                   : Brings in necessary includes and defines from the module.
    #
    'SOURCE'  : {
        'cexc' : {
            'VERSION' : 'V1.00',
            'ARCH'    : "ARM",
            'CORE'    : TARGET['DEVICE'],
            'PREFIX'  : "",
            'BASEDIR' : "",
            'APP'     : "cexc.elf",
            'MAP'     : "cexc.map",
            'DUMP'    : "cexc.dump",
            'HEX'     : "cexc.hex",
#            'HEX2C'   : "cexc.c",
            'HEX_FLAGS' : [
                "-j",".text",
                "-j",".data",
                "-O","ihex",
            ],
#            'HEX2C_FLAGS' : [
#                "bootloader","-AVR","-16",
#            ],
            'DUMP_FLAGS' : [
                "-xdSs",
            ],
            'LISTING'   : "-ahls",
#            'COMMON_DEFS' : [
#                "-DF_CPU="+str(AVR_TARGET['F_CPU_BOOT']),
#                "-DBOOTLOADER_ADDRESS="+str(AVR_TARGET['BOOTLOADER_ADDRESS']),
#            ],
            'DEBUG_DEFS' : [
                "-DDEBUG",
            ],
            'GCC_FLAGS'  : [
                "-Os",
                "-nostdlib",
            ],
            'LDFLAGS' : [
#                "--section-start=.text=%X" % AVR_TARGET['BOOTLOADER_ADDRESS'],
                "-T","ld/"+TARGET["DEVICE"]+".ld",
            ],
            'SRC'     : [
                'app/cr_startup_lpc11xx.c',
                'app/sysinit.c',
                'app/blinky.c',
                'libs/lpc_chip_11uxx_lib/src/sysinit_11xx.c',
                'libs/lpc_chip_11uxx_lib/src/sysctl_11xx.c',
                'libs/lpc_chip_11uxx_lib/src/chip_11xx.c',
                'libs/lpc_chip_11uxx_lib/src/timer_11xx.c',
                'libs/lpc_chip_11uxx_lib/src/clock_11xx.c',
               'libs/lpc_chip_11uxx_lib/src/romdiv_11xx.c',
            ],
            'INCLUDE' : [
                ".",
                "libs/lpc_chip_11uxx_lib/inc/",
#                "configuration/"+AVR_TARGET["DEVICE"]+"/"+AVR_TARGET["BOARD"],
            ],
#            'CHECK_BOOTLOADER_ADDRESS' : True,
#            'ORDER' : 1,
        },
   },

    'DOCS'  : ["docs/Doxyfile_html"],
}

### Main Build Steps
def external():
    module_maker(BUILD,'EXTERNAL',debug=False)

def compile():
    for debug in BUILD['DEBUG_BUILD']:
        module_maker(BUILD,'SOURCE',debug)

def chk_bootloader():
    if False in BUILD['DEBUG_BUILD']:
        debug = False
    else:
        debug = True

    for module in BUILD['SOURCE']:
        if 'CHECK_BOOTLOADER_ADDRESS' in BUILD['SOURCE'][module]:
            app_file = get_destination_file(
                           get_src_tuple(BUILD,'SOURCE',module,
                                         BUILD['SOURCE'][module]['APP'],
                                         debug))
            run("scripts/chk_bootloader",
                app_file,
                AVR_TARGET["BOOTLOADER_ADDRESS"],
                AVR_DEVICES[AVR_TARGET["DEVICE"]]["MAX_FLASH"],
                AVR_DEVICES[AVR_TARGET["DEVICE"]]["FLASH_PAGE"])

# hexadecimal address for bootloader section to begin. To calculate the best value:
# - make clean; make main.hex; ### output will list data: 2124 (or something like that)
# - for the size of your device (8kb = 1024 * 8 = 8192) subtract above value 2124... = 6068
# - How many pages in is that? 6068 / 64 (tiny85 page size in bytes) = 94.8125
# - round that down to 94 - our new bootloader address is 94 * 64 = 6016, in hex = 1780

def package():
  return

def project():
    compile()
    after()
    chk_bootloader()
    package()

def docs():
    """
    for doc in BUILD['DOCS']:
        run(BUILD['TOOLS']['DOC']['GEN'],
            doc,
            group=doc+'_docs')
    """
    return

## Custom Operations

def build():
    external()
    after() # Do not proceed to build source until external builds finish.
    project()
    after()
    docs()

def debug():
    BUILD['DEBUG_BUILD'] = [True]
    build()

def default():
    build()

def clean():
    autoclean()

def usage():
    help(scripts.fabricate)

if __name__ == "__main__":
   main(parallel_ok=False,debug=True )
