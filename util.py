#!/usr/bin/env python3

"""Utility operations for the Fabricate build tool.

fabricate is a build tool that finds dependencies automatically for any
language. It's small and just works. No hidden stuff behind your back. It was
inspired by Bill McCloskey's make replacement, memoize, but fabricate works on
Windows as well as Linux.

These functions are not part of fabricate core, but ease writing build scripts
with it.

"""
import os
import sys
import subprocess
import atexit
import re
import glob
from pathlib import Path

from . import fabricate as FAB

# Function to flatten an array of arrays to make it easy to generate lists of options.
FLATTEN = lambda z: [x for y in z for x in y]

# Interleave an array with a set value.  Useful for building INCLUDE Definitions.
# Eg, INCS = INTERLEAVE('-I', ['a/b', 'a/c'])
INTERLEAVE = lambda y,z: FLATTEN([[y, x] for x in z])

def FILTER(array, excludes):
    """ Take an array of items, and remove all occurrences of anything in
    the exclude array that is found in it.
    Then return the filtered array
    """
    for element in array:
        try:
            if excludes.index(element) >= 0:
                array.remove(element)
        except:
            pass
    return array

def get_flag(FLAGS, PATH):
    """ Get a specific set of flags from a known path. """
    # Return an empty list when there are no flags.
    if FLAGS is None:
        return []

    # If the path is exhausted, return the result as whats left.
    if PATH == []:
        return FLAGS

    return get_flag(FLAGS.get(PATH[0]), PATH[1:])



# Recursively iterate through a dictionary defining compiler flags and
# return the set of flags for a particular TOOL, TYPE and DEVICE
def get_flags(FLAGS, TOOL):
    # TOOL is a tuple of:
    #  (TOOL, TYPE, DEVICE), eg.
    #  ("GCC", "DEBUG", "SAML21G18B")

    # Return an empty list when there are no flags.
    if FLAGS is None:
        return []

    # If the flags are an array, then we return the array as the flags.
    if not isinstance(FLAGS,dict):
        return FLAGS

    # When the flags are a dictionary, we extract the flags from it.
    flags = []
    flags = flags + get_flags(FLAGS.get('COMMON'), TOOL )           # COMMON     - At all levels
    flags = flags + get_flags(FLAGS.get(TOOL[0]+'_FLAGS'), TOOL)    # TOOL_FLAGS - Normally only at root
    flags = flags + get_flags(FLAGS.get(TOOL[1]), TOOL)             # TYPE       - At all levels (DEBUG or RELEASE)

    # Special handling for targets.
    if isinstance(FLAGS.get("DEVICE"), dict):
        flags = flags + get_flags(FLAGS.get("DEVICE").get(TOOL[2]), TOOL)
                                                                    # DEVICE     - Normally at all levels, except root. (Eg. "SAML21G18B")
    return flags

def _mkdir_recursive(path):
    # Make a path, use mkdir if we can, so that clean can remove it.
    sub_path = os.path.dirname(path)

    if (sub_path != "") and (not os.path.exists(sub_path)):
        _mkdir_recursive(sub_path)

    if not os.path.exists(path):
        if sys.platform.startswith('linux'):
            # Linux-specific code here...
            FAB.run("mkdir", "-p", path)
        else:
            # If building on anything other than linux,
            # this should work, but clean wont remove the
            # created directories.
            os.mkdir(path)

def out_name(build_dir, source, out_ext):
    # Create a Output file name, based on the input.
    file_path = os.path.normpath(os.path.join(build_dir, source[0]))

    # Make the build path, if it does not exist
    if not os.path.exists(file_path):
        _mkdir_recursive(file_path)

    return os.path.join(file_path, source[1]+out_ext)

def in_name(source):
    # Create a Input file name, based on the input.
    return os.path.join(source[0], source[1] + source[2])

def split_source(source):
    source_path, source_name = os.path.split(source)
    source_name, source_ext  = os.path.splitext(source_name)

    return (source_path, source_name, source_ext)

def replace_ext(fname,ext):
    return os.path.normpath(os.path.splitext(fname)[0]+ext)

def join_path(*args):
    return os.path.normpath(os.path.join(*args))

def get_build_dir(build,buildtype):
    return build['BUILDS'][buildtype]

def get_destination_file(src,new_ext=None,just_dir=False):
    strip = src[2]
    dest  = src[0]

    if just_dir:
        dest = os.path.dirname(dest)
    elif new_ext != None:
        dest = replace_ext(dest,new_ext)


    if strip > 0:
        dest = dest.split('/',strip)
        dest = dest[len(dest)-1]

    return join_path(src[1],dest)

def get_base_dir(build,section,module):
    if 'BASEDIR' in build[section][module]:
        base_dir = build[section][module]['BASEDIR']
    else:
        base_dir = build[section][module]['VERSION']

    if 'PREFIX' in build[section][module]:
        base_dir = join_path(build[section][module]['PREFIX'],base_dir)

    return base_dir

def get_src_tuple(build,section,module,src,buildtype):
    # The src tuple is:
    # ( "Path to source file",
    #   "Path to locate destination built file",
    #   <number of elements to remove from source when adding to destination> )
    if not isinstance(src, (tuple)):
        src = (src,
                join_path(get_build_dir(build,buildtype),
                          build[section][module]['ARCH'],
                          build[section][module]['CORE']),
               0)

    base_dir = get_base_dir(build,section,module)
    src = (join_path(base_dir,src[0]),src[1],src[2])
    return src

# Returns the name of the tool to build the source file with
def get_tool(build,path):
    ext = os.path.splitext(path[0])[1]
    for tool in build['EXT']:
        if ext in build['EXT'][tool]:
            return tool
    return "Unknown"

# Generic Include Path Collector for GCC and G++
def get_includes(build,section,module,include_uses=True,system=False,buildtype=None):
    base_dir = get_base_dir(build,section,module)
    incs = []
    if system:
        if 'SYSINCLUDE' in build['SOURCE'][module]:
            incs = build['SOURCE'][module]['SYSINCLUDE']
    else:
        if 'INCLUDE' in build['SOURCE'][module]:
            incs = build['SOURCE'][module]['INCLUDE']

    mod_inc  = [join_path(base_dir,inc) for inc in incs]

    if include_uses and ('USES' in build['SOURCE'][module]) :
        for used_module in build['SOURCE'][module]['USES'] :
            mod_inc = mod_inc + get_includes(build,section,used_module,include_uses=False,system=system,buildtype=buildtype)
            mod_inc = mod_inc + [join_path(get_src_tuple(build,section,used_module,"",buildtype)[1],
                                get_base_dir(build,section,used_module))]

    return mod_inc

def add_option(option, group, buildtype, current_option, prefix="", postfix=""):
    if option in group:
        current_option += [prefix + s + postfix for s in group[option]]
    if option+':'+buildtype in group:
        current_option += [prefix + s + postfix for s in group[option+':'+buildtype]]
    return current_option

# Check if a tool name is part of the tool option found.
def tool_compare(tool, toolopt):
    # Literal Name
    if tool == toolopt:
        return True
    # At the begining of a list of tools.
    if toolopt.startswith(tool+':'):
        return True
    # At the end of a list of tools.
    if toolopt.endswith(':'+tool):
        return True
    # In the middle of a list of tools.
    return ':'+tool+':' in toolopt

# Generic Option Collector for GCC and G++
def get_gcc_opt(build,section,module,tool,arch,core,src,buildtype):
    gcc_opt = []

    for toolopt in build['OPTS']:
        if tool_compare(tool, toolopt):
            gcc_opt = add_option('WARN'   ,build['OPTS'][toolopt],buildtype,gcc_opt)
            gcc_opt = add_option('CFLAGS' ,build['OPTS'][toolopt],buildtype,gcc_opt)
            gcc_opt = add_option('DEFINES',build['OPTS'][toolopt],buildtype,gcc_opt,prefix="-D")

            if (arch in build['OPTS'][tool]):
                gcc_opt = add_option('CFLAGS',build['OPTS'][toolopt][arch],buildtype,gcc_opt)
                gcc_opt = add_option(core,build['OPTS'][toolopt][arch],buildtype,gcc_opt)
            else:
                print ("WARNING: Unknown GCC %s Compiler: %s, can not properly compile: %s [%s]" % (arch, core, src[0], module))

    gcc_opt = add_option('DEFINES',build[section][module],buildtype,gcc_opt,prefix="-D")

    # Also get any DEFINES from Used Libraries and Modules
    if ('USES' in build[section][module]) :
        for used_module in build[section][module]['USES'] :
            gcc_opt = add_option('DEFINES',build[section][used_module],buildtype,gcc_opt,prefix="-D")

    return gcc_opt

def get_ld_opt(build,section,module,tool,arch,core,src,buildtype):
    ld_opt = []

    for toolopt in build['OPTS']:
        if tool_compare(tool, toolopt):
            ld_opt = add_option('LDFLAGS',build['OPTS'][toolopt],buildtype,ld_opt)

            if (arch in build['OPTS'][tool]):
                ld_opt = add_option('LDFLAGS',build['OPTS'][toolopt][arch],buildtype,ld_opt)

    return ld_opt

# file finder, makes adding multiple files easier.
def all_files_in(basedir, ext, recursive=False):
    if recursive:
        globpath = os.path.join(basedir, '**', '*'+ext)
    else:
        globpath = os.path.join(basedir, '*'+ext)
    files = []
    for filename in glob.iglob(globpath, recursive=True):
        files.append(filename)

    return files

# directory finder, finds all directories holding files with an extension.
def all_directories_of(basedir, ext):
    globpath = os.path.join(basedir, '**', '*'+ext)

    files = []
    for filename in glob.iglob(globpath, recursive=True):
        filepath = Path(filename)
        basedir = str(filepath.parent)
        if basedir not in files:
            files.append(basedir)

    return files

# Make sure the Build Types have a unique path
def validate_build_types ( buildtypes ):
    paths = []
    for key,value in buildtypes.items():
        if value not in paths:
            paths.append(value)
        else:
            print ("ERROR: BUILD \"%s\" does not have a unique path (%s).  Can not continue." % (key,value))
            exit(1)
    return True
        

