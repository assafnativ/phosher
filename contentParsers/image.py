
import os
import sys
import shutil
from optparse import OptionParser

from phosher.nokiaFile import NokiaFile
from phosher.fat16.parser import parseImage as parseFAT16
from phosher.fat16 import patcher
from phosher.general.util import *

def main():
    userOptions = OptionParser()
    userOptions.add_option("-p", "--patches",   dest="patchesFile", type="string", help="Python scriptin that defines global var PATCHES. The file would be executed!")
    userOptions.add_option("-i", "--input",     dest="inputFile",   type="string", help="Input Image file. It is also possible to set a global INPUT_FILE var in the PATCHES file")
    userOptions.add_option("-o", "--output",    dest="outputFile",  type="string", help="Output file. If not set the output file is dervid from the input file name")
    userOptions.add_option("-d", "--dump",      dest="isDump",      action="store_true", help="Dump files in image to disk")
    userOptions.add_option("-u", "--dumpDest",  dest="dumpDest",    type="string", help="Where to dump files from image")
    userOptions.add_option("-c", "--createIma", dest="createIma",   action="store_true", help="Create FAT16 image file")
    userOptions.add_option("-w", "--imageName", dest="imageName",   type="string", help="Destination FAT16 image file")
    userOptions.add_option("-l", "--list",      dest="listFiles",   action="store_true", help="Display list of all files in image as tree")
    userOptions.add_option("-v", "--verbose",   dest="isVerbose",   action="store_true", help="Set verbose output on")
    userOptions.set_defaults(inputFile=None, outputFile=None, isVerbose=False)
    (options, args) = userOptions.parse_args(sys.argv[1:])
    patchesFile = options.patchesFile
    inputFile   = options.inputFile
    outputFile  = options.outputFile
    isDump      = options.isDump
    dumpDest    = options.dumpDest
    createIma   = options.createIma
    imageName   = options.imageName
    listFiles   = options.listFiles
    isVerbose   = options.isVerbose
    PATCHES, patchesDefines = loadPatchesFromFile(patchesFile, userOptions, isVerbose, globs=patcher)
    inputFile = cmdLineInputFile(patchesDefines, inputFile, userOptions)
    outputFile = cmdLineOutputFile(patchesDefines, outputFile, inputFile)
    if None == dumpDest:
        writeOutput = False
    else:
        writeOutput = True
    if "DUMP_DEST" not in patchesDefines and None == dumpDest:
        dumpDest = inputFile + '_DUMP'
    elif "DUMP_DEST"   in patchesDefines and None == dumpDest:
        dumpDest = patchesDefines["DUMP_DEST"]
    if "IMAGE_FILE" not in patchesDefines and None == imageName:
        imageName = inputFile + '.ima'
    elif "IMAGE_FILE"   in patchesDefines and None == imageName:
        imageName = IMAGE_FILE
    nokiaFile = NokiaFile(inputFile, isVerbose=isVerbose)
    imageData = nokiaFile.plain

    fat16 = parseFAT16(imageData, isVerbose=isVerbose)

    if None != patchesFile:
        writeOutput = True
        fat16Patcher = patcher.Fat16Patcher(fat16)
        fat16Patcher.patch(PATCHES)
    if isDump:
        fat16.dumpTree(dumpDest)
    if createIma:
        imageData = fat16.makeNoPadding()
        file(imageName, 'wb').write(imageData)
    if listFiles:
        print fat16.displayTree()
    if writeOutput:
        nokiaFile.plain = fat16.make()
        file(outputFile, 'wb').write(nokiaFile.encode())

if __name__ == "__main__":
    main()
