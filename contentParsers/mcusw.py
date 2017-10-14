
import os
import sys
from optparse import OptionParser

from phosher.nokiaFile import NokiaFile
from phosher.general.util import *
from struct import unpack, pack

def fixChecksum(base, plain, nokiaFile, isVerbose):
    endAddress = base + len(plain) - 1
    if 0xA2 == nokiaFile.fileType:
        # DCT-4 fix check sum
        currentEnd = unpack('>L', plain[0xfc:0xfc+4])[0]
        if currentEnd != endAddress:
            printIfVerbose("Changing ending address from 0x%x to 0x%x" % (currentEnd, endAddress), isVerbose)
            plain = plain[:0xfc] + pack('>L', endAddress) + plain[0x100:]
        start = unpack('>L', plain[0x78:0x78+4])[0]
        start -= base
        dataToCheck = plain[start:]
        dataToCheckLen = len(dataToCheck)
        dataWords = unpack('>' + ('H' * (dataToCheckLen / 2)), dataToCheck)
        checksum = sum(dataWords) & 0xffff
        currentChecksum = unpack('>H', plain[0x26:0x26+2])[0]
        if currentChecksum != checksum:
            printIfVerbose("Current checksum 0x%x fixing to 0x%x" % (currentChecksum, checksum), isVerbose)
            plain = plain[:0x26] + pack('>H', checksum) + plain[0x28:]
    return plain

def patchValueToBin(val):
    return val.replace('\n', '').replace(' ', '').replace('\r', '').replace('\t', '').decode('hex')

def patchMcusw(base, plain, nokiaFile, patches, isVerbose):
    plainLen = len(plain)
    endAddr = base + plainLen
    for patchName, patchAddr, oldValue, newValue in patches:
        if (patchAddr < base):
            raise Exception("Can't write patch %s - Invalid address 0x%x (Valid addresses start at 0x%x)" % (patchName, patchAddr, base))
        if 0xa2 == nokiaFile.fileType and patchAddr > 0x1000100 and patchAddr < 0x1100100:
            print("Warnning patching bytes at the first MB on a DCT4 firmware")
        newValueBin = patchValueToBin(newValue)
        newValueHex = newValueBin.encode('hex')
        patchOffset = patchAddr - base
        patchLength = len(newValueBin)
        patchEndOffset = patchOffset + patchLength
        if patchEndOffset > plainLen:
            # This patch is of append bytes
            if None != oldValue:
                raise Exception("Patch %s error. If you are trying to append bytes to file, set old value to None" % patchName)
            missingBytes = patchAddr - endAddr
            if 0 > missingBytes:
                raise Exception("Patch %s error. If you are trying to append bytes to file, please do it in a single patch" % patchName)
            elif 0 < missingBytes:
                plain += '\xff' * missingBytes
            printIfVerbose("Patch %s: Appending bytes %s" % (patchName, newValueHex), isVerbose)
            plain += newValueBin
            plainLen = len(plain)
            endAddr = base + plainLen
        else:
            oldValueBin = patchValueToBin(oldValue)
            oldValueHex = oldValueBin.encode('hex')
            if len(oldValueBin) != len(newValueBin):
                raise Exception("Old value is of different length of new value - this is invalid")
            origValue = plain[patchOffset:patchEndOffset]
            if origValue != oldValueBin:
                raise Exception("Patch %s error: Old value mismatch - %s -> %s" % (patchName, origValue.encode('hex'), oldValueHex))
            printIfVerbose("Patch %s: Patching %s -> %s (@0x%x" % (patchName, oldValueHex, newValueHex, patchAddr), isVerbose)
            plain = plain[:patchOffset] + newValueBin + plain[patchEndOffset:]
    return plain

def makeMcusw(inputFile, outputFileName, patchesFile=None, isDumpPlain=False, dumpDest=None, dontFixChecksum=False, isVerbose=False):
    PATCHES, patchesDefines = loadPatchesFromFile(patchesFile, isVerbose)
    inputFile   = cmdLineInputFile(patchesDefines, inputFile)
    outputFileName  = cmdLineOutputFile(patchesDefines, outputFileName, inputFile)
    nokiaFile = NokiaFile(inputFile, isVerbose=isVerbose)
    plain = nokiaFile.plain
    plainAddr = nokiaFile.address

    if None != patchesFile:
        plain = patchMcusw(plainAddr, plain, nokiaFile, PATCHES, isVerbose)
        nokiaFile.plain = plain
    if False == dontFixChecksum:
        plain = fixChecksum(plainAddr, plain, nokiaFile, isVerbose)
        nokiaFile.plain = plain
    if isDumpPlain:
        dumpDest = cmdLineDumpDestFile(patchesDefines, dumpDest, outputFileName, plainAddr)
        with open(dumpDest, 'wb') as dumpFile:
            dumpFile.write(plain)
    mcuData = nokiaFile.encode()
    with open(outputFileName, 'wb') as outputFile:
        outputFile.write(mcuData)

def main():
    userOptions = OptionParser()
    userOptions.add_option("-p", "--patches",   dest="patchesFile", type="string", help="Python scriptin that defines global var PATCHES. The file would be executed!")
    userOptions.add_option("-i", "--input",     dest="inputFile",   type="string", help="Input MCUSW file. It is also possible to set a global INPUT_FILE var in the PATCHES file")
    userOptions.add_option("-o", "--output",    dest="outputFile",  type="string", help="Output file. If not set the output file is dervid from the input file name")
    userOptions.add_option("-d", "--plain",     dest="dumpPlain",   action="store_true", help="Save the plain (deobfuscated) data to file")
    userOptions.add_option("-u", "--plainDst",  dest="dumpDest",    type="string", help="Where to dump plain data to")
    userOptions.add_option("-v", "--verbose",   dest="isVerbose",   action="store_true", help="Set verbose output on")
    userOptions.add_option("-z", "--dontFixChecksum", dest="dontFixChecksum", action="store_true", help="Don't fix the plain checksum")
    userOptions.set_defaults(inputFile=None, outputFile=None, isVerbose=False, dumpDest=None, dumpPlain=False, dontFixChecksum=False)
    (options, args) = userOptions.parse_args(sys.argv[1:])
    patchesFile = options.patchesFile
    inputFile   = options.inputFile
    outputFile  = options.outputFile
    isDumpPlain = options.dumpPlain
    dumpDest    = options.dumpDest
    isVerbose   = options.isVerbose
    dontFixChecksum = options.dontFixChecksum
    return makeMcusw(inputFile, outputFile, patchesFile, isDumpPlain, dumpDest, dontFixChecksum, isVerbose)

if __name__ == "__main__":
    main()
