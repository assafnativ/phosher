
import os
import sys
from optparse import OptionParser

from phosher.nokiaFile import NokiaFile
from phosher.general.util import *

def main():
    userOptions = OptionParser()
    userOptions.add_option("-i", "--input",     dest="inputFile",   type="string", help="Input file")
    userOptions.add_option("-o", "--output",    dest="outputFile",  type="string", help="Where to save plain data")
    userOptions.add_option("-v", "--verbose",   dest="isVerbose",   action="store_true", help="Set verbose output on")
    userOptions.set_defaults(inputFile=None, outputFile=None, isVerbose=False)
    (options, args) = userOptions.parse_args(sys.argv[1:])
    inputFile   = options.inputFile
    outputFile  = options.outputFile
    isVerbose   = options.isVerbose
    inputFile = cmdLineInputFile({}, inputFile, userOptions)
    outputFile = cmdLineOutputFile({}, outputFile, inputFile)

    data = file(inputFile, 'rb').read()
    if len(data) < 0x100:
        raise Exception("Input file too short to be a NokiaFile")

    nokiaFile = NokiaFile(data, isVerbose=isVerbose)

    if None != outputFile:
        file(outputFile, 'wb').write(nokiaFile.plain)

if __name__ == "__main__":
    main()

