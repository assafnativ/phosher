
import os
import sys
import shutil
from optparse import OptionParser

from phosher.nokiaFile import NokiaFile
from phosher.fat16.parser import parseImage as parseFAT16

def patchImage(img, fat16, outputFile, PATCHES):
    fat16Patcher = Fat16Patcher(fat16)
    fat16Patcher.patch(PATCHES)
    img.updateFat16(fat16)
    img.pack()

def main():
    userOptions = OptionParser()
    userOptions.add_option("-p", "--patches",   dest="patchesFile", type="string", help="Python scriptin that defines global var PATCHES. The file would be executed!")
    userOptions.add_option("-i", "--input",     dest="inputFile",   type="string", help="Input Image file. It is also possible to set a global INPUT_FILE var in the PATCHES file")
    userOptions.add_option("-o", "--output",    dest="outputFile",  type="string", help="Output file. If not set the output file is dervid from the input file name")
    userOptions.add_option("-d", "--dump",      dest="isDump",      action="store_true", help="Dump files in image to disk")
    userOptions.add_option("-u", "--dumpDest",  dest="dumpDest",    type="string", help="Where to dump files from image")
    userOptions.add_option("-c", "--createIma", dest="createIma",   action="store_true", help="Create FAT16 image file")
    userOptions.add_option("-w", "--imageName", dest="imageName",   type="string", help="Destination FAT16 image file")
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
    isVerbose   = options.isVerbose
    if None != patchesFile:
        if not os.path.isfile(patchesFile):
            userOptions.error("Patches file not found")
        execfile(patchesFile)
    if "INPUT_FILE" not in globals() and None == inputFile:
        userOptions.error("Please set the input file either in command line or in the PATCHES file")
    if "INPUT_FILE" in globals() and None == inputFile:
        # Command line overwrites PATCHES file
        inputFile = INPUT_FILE
    if not os.path.isfile(inputFile):
        userOptions.error("Invalid input file %s" % inputFile)
    if "OUTPUT_FILE" not in globals() and None == outputFile:
        # Derive the output file name from the input file name
        outputPath = os.path.dirname(inputFile)
        outputFile = os.path.basename(inputFile)
        pos = outputFile.rfind(".")
        if "-1" != pos:
            outputFile = outputFile[:pos] + ".patched" + outputFile[pos:]
        else:
            outputFile = outputFile + ".patched"
    elif "OUTPUT_FILE" in globals() and None == outputFile:
        outputFile = OUTPUT_FILE
    if "IS_NEW_FORMAT" in globals():
        newFormat = IS_NEW_FORMAT
    if "DUMP_DEST" not in globals() and None == dumpDest:
        dumpDest = inputFile + '_DUMP'
    elif "DUMP_DEST"   in globals() and None == dumpDest:
        dumpDest = DUMP_DEST
    if "IMAGE_FILE" not in globals() and None == imageName:
        imageName = inputFile + '.ima'
    elif "IMAGE_FILE"   in globals() and None == imageName:
        imageName = IMAGE_FILE
    nokiaFile = NokiaFile(inputFile)
    imageData = nokiaFile.extractPlain()[1]

    img = parseFAT16(imageData, isVerbose=isVerbose)

    if None != patchesFile:
        outputFile = patchImage(img, fat16, outputFile, PATCHES)
    if isDump:
        img.dumpTree(dumpDest)
    if createIma:
        file(imageName, 'wb').write(img.make())

if __name__ == "__main__":
    main()