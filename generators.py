#!/usr/bin/env python3
from .fabricate import *
from .util      import *

import os
import platform

# Generic Builder for GCC and G++
def gcc(build, section, module, tool, arch, core, src, buildtype):
    gcc_opt = get_gcc_opt(build,section,module,tool,arch,core,src,buildtype)

    # Get Includes
    includes = get_includes(build,section,module,buildtype)
    sysincludes = get_includes(build,section,module,system=True,buildtype=buildtype)

    # Add -I to each include path.
    inc_opt = [['-I',inc] for inc in includes]

    # Add -i to each system include path.
    sysinc_opt = [['-isystem',inc] for inc in sysincludes]

    if 'LISTING' in build[section][module]:
        gcc_opt.extend(["-Wa,%s=%s" % (build[section][module]['LISTING'],get_destination_file(src,new_ext='.lst'))])

    # GCC wont make output directories, so ensure there is a place the output can live.
    output_file = get_destination_file(src,new_ext='.o')
    if not os.path.isdir(os.path.dirname(output_file)):
        os.makedirs(os.path.dirname(output_file))

    tool = [join_path(build['TOOLS']['PATH'][arch],build['TOOLS'][tool][arch])]
    if 'PFX' in build['TOOLS']:
        if arch in build['TOOLS']['PFX']:
            tool = [build['TOOLS']['PFX'][arch]] + tool

    after_modules=()
    if ('USES' in build['SOURCE'][module]) :
        for used_module in build['SOURCE'][module]['USES'] :
            after_modules = after_modules + (used_module,)

    # run GCC
    run(tool,
        gcc_opt,
        inc_opt,sysinc_opt,
        '-c', src[0],
        '-o', output_file,
        group=module,
        after=after_modules)

def ar(build,section,module, buildtype):
    base_dir = get_base_dir(build,section,module)
    arch     = build[section][module]['ARCH']
    core     = build[section][module]['CORE']

    print ("Archiving Library %s of %s" % ( build[section][module]['LIBRARY'],
                                         build[section][module]['VERSION'] ))

    objects = [get_destination_file(
                  get_src_tuple(build,section,module,s,buildtype),
                  new_ext='.o') for s in build[section][module]['SRC']]

    library = get_destination_file(
                  get_src_tuple(build,
                                build[section][module]['LIBRARY'],
                                module,buildtype,section=section))

    output_dir = os.path.dirname(library)

    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)

    # Only safe to run when all objects are build AND the directory it belongs in is made.
    run(join_path(build['TOOLS']['PATH'][arch],
                  build['TOOLS']['AR'][arch]),
        'rcs', library, objects,
        group=build[section][module]['LIBRARY'], after=(module))

def ld(build, section, module, buildtype):
    def add_ldflags(ldflags):
        ext_ldflags = []
        for ldflag in ldflags:
            ext_ldflags.extend(["-Wl,"+ldflag])
        return ext_ldflags

    base_dir = get_base_dir(build,section,module)
    arch     = build[section][module]['ARCH']
    core     = build[section][module]['CORE']

    print ("Linking Application %s of %s" % ( build[section][module]['APP'],
                                             build[section][module]['VERSION'] ))

    gcc_opt =  get_gcc_opt(build,section,module,'LD',arch,core,(""),buildtype)
    gcc_opt += add_ldflags(get_ld_opt(build,section,module,'LD',arch,core,(""),buildtype))

    searchpaths = []
    if 'LINK' in build[section][module]:
        # Make sure we can find link include files.
        searchpaths = searchpaths + [os.path.dirname(build[section][module]['LINK'])]
        gcc_opt.extend(["-T,",build[section][module]['LINK']])

    searchpaths = [["-Wl,-L,"+path] for path in searchpaths]

    # Get Objects to link
    objects = [get_destination_file(
                  get_src_tuple(build,section,module,s,buildtype),
                  new_ext='.o') for s in build[section][module]['SRC']]

    output_file = get_destination_file(
                      get_src_tuple(build,section,module,
                                    build[section][module]['APP'],
                                    buildtype))

    mapfile = None
    if 'MAP' in build[section][module]:
      mapfile = "-Wl,-Map="+get_destination_file(
                                get_src_tuple(build,section,module,
                                    build[section][module]['MAP'],
                                    buildtype))


    # run GCC - to link
    run(join_path(build['TOOLS']['PATH'][arch],build['TOOLS']['GCC'][arch]),
        gcc_opt,
        objects,
        mapfile,
        searchpaths,
        '-o', output_file,
        group=module+'_link',
        after=(module))


def src_build(build,section,module,buildtype):
    # Build a bunch of source files, based on their extensions.
    for src in build[section][module]['SRC']:
        clean_src = src
        src = get_src_tuple(build,section,module,clean_src,buildtype)
        tool = get_tool(build, src)

        if ((tool == 'GCC') or (tool == 'GXX') or (tool == 'GAS')):
            gcc(build,
                section,
                module,
                tool,
                build[section][module]['ARCH'],
                build[section][module]['CORE'],
                src,
                buildtype)
        else:
            print ("%s ERROR: Don't know how to compile : %s from %s using %s" % (section, src, module, tool))
            exit(1)

def gen_hex(build,section,module,buildtype):
    base_dir = get_base_dir(build,section,module)
    arch     = build[section][module]['ARCH']
    core     = build[section][module]['CORE']

    print ("Making .hex of Application %s/%s" % ( build[section][module]['APP'],
                                             build[section][module]['VERSION'] ))

    app_file = get_destination_file(
                      get_src_tuple(build,section,module,
                                    build[section][module]['APP'],
                                    buildtype))

    hex_file = get_destination_file(
                      get_src_tuple(build,section,module,
                                    build[section][module]['HEX'],
                                    buildtype))

    # run obj-copy - to generate .hex file
    run(join_path(build['TOOLS']['PATH'][arch],build['TOOLS']['OBJ-COPY'][arch]),
        build[section][module]["HEX_FLAGS"],
        app_file, hex_file,
        group=module+'_hex',
        after=(module+'_link'))

def gen_dump(build,section,module,buildtype):
    base_dir = get_base_dir(build,section,module)
    arch     = build[section][module]['ARCH']
    core     = build[section][module]['CORE']

    print ("Making .dump of Application %s/%s" % ( build[section][module]['APP'],
                                             build[section][module]['VERSION'] ))

    app_file = get_destination_file(
                      get_src_tuple(build,section,module,
                                    build[section][module]['APP'],
                                    buildtype))

    dump_file = get_destination_file(
                      get_src_tuple(build,section,module,
                                    build[section][module]['DUMP'],
                                    buildtype))

    # run obj-dump - to generate dump of the compiled code
    run(join_path(build['TOOLS']['PATH']['SCRIPT'],'capture_stdout'),
        join_path(build['TOOLS']['PATH'][arch],build['TOOLS']['OBJ-DUMP'][arch]),
        dump_file,
        build[section][module]["DUMP_FLAGS"],
        app_file,
        group=module+'_dump',
        after=(module+'_link'))

def gen_hex2c(build,section,module,buildtype):
    base_dir = get_base_dir(build,section,module)
    arch     = build[section][module]['ARCH']
    core     = build[section][module]['CORE']

    print ("Making .c of Application %s/%s" % ( build[section][module]['APP'],
                                             build[section][module]['VERSION'] ))

    hex_file = get_destination_file(
                      get_src_tuple(build,section,module,
                                    build[section][module]['HEX'],
                                    buildtype)) 

    c_file = get_destination_file(
                      get_src_tuple(build,section,module,
                                    build[section][module]['HEX2C'],
                                    buildtype))

    # run hex2c - to generate .x file
    run(join_path(build['TOOLS']['PATH']['SCRIPT'],'hex2c'),
        hex_file,
        c_file,
        build[section][module]["HEX2C_FLAGS"],
        group=module+'_hex2c',
        after=(module+'_hex'))



def module_maker(build,section='SRC', buildtype = None):

    # Dictionaries are inherently unsorted.
    # To ensure sources are built in a particular order put an
    # "ORDER" key in the source module and number it in ascending
    # priority.  by default everything is Order 1.  they are built
    # first in arbitrary order.  Then Order 2 and so on.
    def module_sorter(module):
        order = 1
        if "ORDER" in build[section][module]:
            order = build[section][module]["ORDER"]
        return order

    for module in sorted(build[section],key=module_sorter):
        cmd_cnt = 0;

        if (module not in build['SKIP']):

            src_build(build,section,module,buildtype)
            
            after()

            # Source files need to be linked.
            #   Depending on the kind of source, link as appropriate.
            #   Each option is Mutually Exclusive
            if ('LIBRARY' in build[section][module]) :
                ar(build,module,buildtype,section)
            elif ('MODULE' in build[section][module]) :
                """
                Modules are linked with their APP!
                NOTHING TO DO NOW.
                """
            elif ('APP' in build[section][module]) :
                ld(build,section,module,buildtype)

            # generate any .hex files as required.
            if ('HEX' in build[section][module]):
                gen_hex(build,section,module,buildtype)

            # generate .c files as required.
            if ('HEX2C' in build[section][module]):
                gen_hex2c(build,section,module,buildtype)

            # generate .dump files as required.
            if ('DUMP' in build[section][module]):
                gen_dump(build,section,module,buildtype)
