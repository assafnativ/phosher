
import os
import sys
import shutil
from struct import pack, unpack
from hashlib import sha1
from optparse import OptionParser

from phosher.nokiaFile import NokiaFile
from phosher.general.util import *
from phosher.general.objectWithStream import *

class PPMSection(object):
    def __init__(self, isVerbose=False):
        self.isVerbose = isVerbose
    def calcCheckSum(self, block):
        return sum(unpack('<' + ('L' * (len(block) / 4)), block)) & 0xffffffff
    def parseFromStream(self, stream):
        self.startPos = stream.tell()
        self.checksum, self.length, chunk = readCLTVChunk(stream)
        self.rawData = pack('<LL', self.checksum, self.length) + chunk.peekOnRestOfData()
        self.name    = chunk.read(4)[::-1]
        self.version = chunk.read(8)
        if 'DUMFILE\x00' == self.version or 'LDB\x00' == self.name:
            return
        printIfVerbose("Section %s at %x of %x bytes" % (self.name.replace('\x00', ' '), self.startPos, self.length), self.isVerbose)
        self.calcedChecksum = self.calcCheckSum(chunk.getRawData())
        if self.checksum != self.calcedChecksum:
            printIfVerbose("Checksum mismatch: %x <-> %x" % (self.checksum, self.calcedChecksum), self.isVerbose)
        self.subSections = []
        while chunk.tell() < (self.length - 4):
            subSection = PPMSubSection()
            subSection.parseFromStream(chunk, self)
            self.subSections.append(subSection)

    def toBinary(self):
        if 'DUMFILE\x00' == self.version or 'LDB\x00' == self.name:
            return self.rawData
        result = ObjectWithStream()
        # Save place for checksum
        result.writeUInt32(0)
        # Save place for length
        result.writeUInt32(0)
        result.write(self.name[::-1])
        result.write(self.version)
        for subSection in self.subSections:
            result.write(subSection.toBinary())
        length = result.tell()
        result.seek(4,0)
        if self.length != length:
            print("! Section %s has changed its length (%x -> %x)" % (self.name, self.length, length))
        self.length = length
        result.writeUInt32(self.length)
        result.seek(4,0)
        rawData = result.read()
        result.seek(0, 0)
        result.writeUInt32(self.calcCheckSum(rawData))
        return result.getRawData()

class PPMSubSection(object):
    def __init__(self, isVerbose=False):
        self.isVerbose = isVerbose
        self.SECTIONS_PARSERS = {
                'TEXT':     self.parseText,
                'EDIT' :    self.parseEdit,
                'AORD' :    self.parseAord,
                'LDB\x00' : self.parseLdb,
                'CDB\x00' : self.parseCdb,
                'ANIM' :    self.parseAnim,
                'SIND' :    self.parseSind,
                'TONE' :    self.parseTone,
                'VFNT' :    self.parseVfnt,
                'PLMN' :    self.parsePlmn,
                'LPCS' :    self.parseLpcs,
                'GSMC' :    self.parseGsmc,
                'PALE' :    self.parsePale,
                'SCHM' :    self.parseSchm,
                'THEM' :    self.parseThem }
        self.SECTIONS_BUILDER = {
                'TEXT':     self.buildText,
                'EDIT' :    self.buildEdit,
                'AORD' :    self.buildAord,
                'LDB\x00' : self.buildLdb,
                'CDB\x00' : self.buildCdb,
                'ANIM' :    self.buildAnim,
                'SIND' :    self.buildSind,
                'TONE' :    self.buildTone,
                'VFNT' :    self.buildVfnt,
                'PLMN' :    self.buildPlmn,
                'LPCS' :    self.buildLpcs,
                'GSMC' :    self.buildGsmc,
                'PALE' :    self.buildPale,
                'SCHM' :    self.buildSchm,
                'THEM' :    self.buildThem }
    def parseFromStream(self, stream, parent):
        self.parent = parent
        self.startPos = stream.tell()
        self.sectionId = stream.readUInt32()
        if 0 == self.sectionId:
            self.raw = stream.read()
            return
        self.length, subSection = readLTVChunk(stream, prefetchedBytes=4)
        self.name = subSection.read(4)
        self.flags = []
        self.flags.append(subSection.readUInt8())
        self.flags.append(subSection.readUInt8())
        self.flags.append(subSection.readUInt8())
        self.flags.append(subSection.readUInt8())
        self.stream = subSection
        #printIfVerbose("\tSub (%x) section %s at %x of %s bytes" % (self.sectionId, self.name, self.startPos, self.length), self.isVerbose)
        sectionType = self.parent.name
        if sectionType in self.SECTIONS_PARSERS:
            self.SECTIONS_PARSERS[sectionType]()
        else:
            print("Unknown section type %s" % repr(sectionType))

    def toBinary(self):
        result = ObjectWithStream()
        result.writeUInt32(self.sectionId)
        if 0 == self.sectionId:
            result.write(self.raw)
            return result.getRawData()
        # Save place for the length
        result.writeUInt32(0)
        result.write(self.name)
        for flag in self.flags:
            result.writeUInt8(flag)
        sectionType = self.parent.name
        if sectionType in self.SECTIONS_BUILDER:
            result.write(self.SECTIONS_BUILDER[sectionType]())
        else:
            raise Exception("Don't know how to build section of type %s" % sectionType)
        if result.tell() != self.length:
            printIfVerbose("! Section %s of type %s has changed its length (%x -> %x)" % (self.name, sectionType, self.length, result.tell()), self.isVerbose)
        self.length = result.tell()
        result.seek(4, 0)
        result.writeUInt32(self.length)
        return result.getRawData()

    def parseAnim(self):
        result = []
        stream = self.stream
        if 0 == self.sectionId:
            self.raw = stream.read()
            return
        self.numEntries = stream.readUInt32()
        animationsInfo = []
        for i in range(self.numEntries):
            animationIndex  = stream.readUInt16()
            animationUnk    = stream.readUInt16()
            animationOffset = stream.readUInt32()
            animationUnk2   = stream.readUInt32()
            animationsInfo.append((
                    animationIndex,
                    animationUnk,
                    animationOffset,
                    animationUnk2))
        self.animations = []
        if 0 < self.numEntries:
            lastIndex, lastUnk, startOffset, lastUnk2 = animationsInfo[0]
            for index, unk, endOffset, unk2 in animationsInfo[1:]:
                data = stream.read(endOffset - startOffset)
                self.animations.append((lastIndex, lastUnk, lastUnk2, data))
                startOffset = endOffset
                lastIndex = index
                lastUnk = unk
                lastUnk2 = unk2
            # Add last one
            data = stream.read()
            self.animations.append((index, unk, unk2, data))

    def buildAnim(self):
        if 0 == self.sectionId:
            return self.raw
        result = ObjectWithStream()
        result.writeUInt32(len(self.animations))
        totalLength = 0
        for index, unk, unk2, data in self.animations:
            result.writeUInt16(index)
            result.writeUInt16(unk)
            result.writeUInt32(totalLength)
            result.writeUInt32(unk2)
            totalLength += len(data)
        for index, unk, unk2, data in self.animations:
            result.write(data)
        return result.getRawData()

    def parseText(self):
        self.raw = self.stream.read()
        return

        # Canceld for now - Use trix
        #printIfVerbose("\t\tParsing TEXT section subSection %s" % self.name, self.isVerbose)
        result = []
        stream = self.stream
        flags = self.flags
        if 0 == self.sectionId:
            self.raw = stream.read()
            return
        if flags[0] & 0x10:
            self.compression = 1
        elif flags[0] & 0x20:
            self.compression = 2
        else:
            self.compression = 0
        self.isTwoBytesLen = 0 != (flags[0] & 0x40)
        self.isUTF16 = 0x80 == (flags[0] & 0x84)
        self.raw = stream.peekOnRestOfData()
        if 0 == self.compression:
            self.texts = self.parseTextNotCompressed()
        else:
            self.texts = self.parseTextCompressed()

    def parseTextNotCompressed(self):
        stream = self.stream
        numItems = stream.readUInt16()
        lengths = []
        for i in range(numItems):
            if self.isTwoBytesLen:
                entryLength = stream.readUInt16()
            else:
                entryLength = stream.readUInt8()
            if 0xfeff <= entryLength:
                raise Exception("Length error")
            if self.isUTF16:
                entryLength *= 2
            lengths.append(entryLength)
        texts = []
        for i, length in enumerate(lengths):
            newString = stream.read(length)
            if self.isUTF16:
                #printIfVerbose('\t\t\t%x %s' % (stream.tell(), newString.decode('UTF16')), self.isVerbose)
                pass
            else:
                #printIfVerbose('\t\t\t%x %s' % (stream.tell(), newString), self.isVerbose)
                pass
            texts.append(newString)
        sectionLen = self.length
        return texts

    def parseTextCompressed(self):
        stream = self.stream
        texts = []
        return texts
    
    def buildTextNotCompressed(self):
        result = ObjectWithStream()
        result.writeUInt16(len(self.texts))
        for text in self.texts:
            textLen = len(text)
            if self.isUTF16:
                textLen /= 2
            if self.isTwoBytesLen:
                result.writeUInt16(textLen)
            else:
                result.writeUInt8(textLen)
        for text in self.texts:
            result.write(text)
        return result.getRawData()

    def buildText(self):
        return(self.raw)

        # Canceld for now - Use Trix
        if 0 == self.sectionId:
            return self.raw
        if 0 == self.compression:
            return self.buildTextNotCompressed()
        else:
            return self.raw

    def parseEdit(self):
        self.raw = self.stream.read()
    def parseAord(self):
        self.raw = self.stream.read()
    def parseLdb(self):
        self.raw = self.stream.read()
    def parseCdb(self):
        self.raw = self.stream.read()
    def parseSind(self):
        self.raw = self.stream.read()
    def parseTone(self):
        self.raw = self.stream.read()
    def parseVfnt(self):
        self.raw = self.stream.read()
    def parsePlmn(self):
        self.raw = self.stream.read()
    def parseLpcs(self):
        self.raw = self.stream.read()
    def parseGsmc(self):
        self.raw = self.stream.read()
    def parsePale(self):
        self.raw = self.stream.read()
    def parseSchm(self):
        self.raw = self.stream.read()
    def parseThem(self):
        self.raw = self.stream.read()

    def buildEdit(self):
        return(self.raw)
    def buildAord(self):
        return(self.raw)
    def buildLdb(self):
        return(self.raw)
    def buildCdb(self):
        return(self.raw)
    def buildSind(self):
        return(self.raw)
    def buildTone(self):
        return(self.raw)
    def buildVfnt(self):
        return(self.raw)
    def buildPlmn(self):
        return(self.raw)
    def buildLpcs(self):
        return(self.raw)
    def buildGsmc(self):
        return(self.raw)
    def buildPale(self):
        return(self.raw)
    def buildSchm(self):
        return(self.raw)
    def buildThem(self):
        return(self.raw)

def readLTVChunk(stream, prefetchedBytes=0):
    length  = stream.readUInt32()
    subSection = ObjectWithStream()
    subSectionData = stream.read(length - 4 - prefetchedBytes)
    subSection.writeUInt32(length)
    subSection.writeData(subSectionData)
    subSection.seek(4, 0)
    return (length, subSection)

def readCLTVChunk(stream):
    checksum = stream.readUInt32()
    length, subSection = readLTVChunk(stream, prefetchedBytes=4)
    return (checksum, length, subSection)

class PPM(object):
    def __init__(self, ppmData, isVerbose=False):
        self.isVerbose = isVerbose
        self.ppmData = ppmData
        self.parsePPMData(self.ppmData)

    def dumpAnimationsToDisk(self, outputDir):
        if not os.path.isdir(outputDir):
            os.mkdir(outputDir)
            if not os.path.isdir(outputDir):
                raise Exception("Invalid output path")
        for section in self.sections:
            if 'ANIM' == section.name:
                for subSection in section.subSections:
                    if 0 == subSection.sectionId:
                        continue
                    for index, _, _, data in subSection.animations:
                        exten = 'bin'
                        if data.startswith('GIF'):
                            exten = 'gif'
                        elif data.startswith('\x89PNG'):
                            exten = 'png'
                        elif data.startswith('NFIM'):
                            exten = 'nfi'
                        file('%s\\%s_%08d.%s' % (outputDir, subSection.name, index, exten), 'wb').write(data)

    def patch(self, patchList):
        pass

    def parsePPMData(self, ppm):
        if len(ppm) < 0x100:
            ppm = file(ppm, 'rb').read()
        self.ppmLength = len(ppm)
        self.data = ObjectWithStream(ppm)
        magic = self.data.read(4)
        if '\x00MPP' == magic:
            self.data = ObjectWithStream(ppm, endianity='<')
        elif 'PPM\x00' == magic:
            self.data = ObjectWithStream(ppm, endianity='>')
        else:
            raise Exception("Invalid magic in PPM header")
        magic = self.data.read(4)
        self.version = self.data.readString()
        printIfVerbose("PPM version: %s" % self.version, self.isVerbose)
        self.data.seek(0x40, 0)
        self.langId = self.data.read(4)
        printIfVerbose("PPM lang ID: %s" % self.langId.replace('\x00', ''), self.isVerbose)
        self.sections = []
        while True:
            newSection = PPMSection(isVerbose=self.isVerbose)
            newSection.parseFromStream(self.data)
            self.sections.append(newSection)
            if newSection.version == 'DUMFILE\x00':
                break

    def toBinary(self):
        result = ObjectWithStream()

        result.write('\x00MPP')
        result.write(self.version + '\x00')
        while result.tell() < 0x40:
            result.write('\xff')
        result.write(self.langId)
        for section in self.sections:
            result.write(section.toBinary())

        return result.getRawData()

    def make(self):
        return self.toBinary()

def main():
    userOptions = OptionParser()
    userOptions.add_option("-p", "--patches",   dest="patchesFile", type="string", help="Python scriptin that defines global var PATCHES. The file would be executed!")
    userOptions.add_option("-i", "--input",     dest="inputFile",   type="string", help="Input Image file. It is also possible to set a global INPUT_FILE var in the PATCHES file")
    userOptions.add_option("-o", "--output",    dest="outputFile",  type="string", help="Output file. If not set the output file is dervid from the input file name")
    userOptions.add_option("-d", "--dumpAni",   dest="isDumpAnimations", action="store_true", help="Should dump animations")
    userOptions.add_option("-f", "--dumpDest",  dest="dumpOutputDir", type="string", help="Where to dump the animation files")
    userOptions.add_option("-t", "--text",      dest="isText",      action="store_true", help="Output readable version of the PPM")
    userOptions.add_option("-v", "--verbose",   dest="isVerbose",   action="store_true", help="Set verbose output on")
    userOptions.set_defaults(inputFile=None, outputFile=None, isVerbose=False, isText=False, isDumpAnimations=False, dumpDest=None)
    (options, args) = userOptions.parse_args(sys.argv[1:])
    patchesFile = options.patchesFile
    inputFile   = options.inputFile
    outputFile  = options.outputFile
    isDumpAnimations = options.isDumpAnimations
    dumpDest    = options.dumpDest
    isText      = options.isText
    isVerbose   = options.isVerbose

    PATCHES, patchesDefines = loadPatchesFromFile(patchesFile, isVerbose)
    inputFile = cmdLineInputFile(patchesDefines, inputFile)
    outputFile = cmdLineOutputFile(patchesDefines, outputFile, inputFile)

    nokiaFile = NokiaFile(inputFile, isVerbose=isVerbose)
    ppmData = nokiaFile.plain

    ppm = PPM(ppmData, isVerbose=isVerbose)
    if None != patchesFile:
        ppm.patch(PATCHES)
    if None != isDumpAnimations:
        if None == dumpDest:
            dumpDest = inputFile + '.animations'
        ppm.dumpAnimationsToDisk(dumpDest)
    if isText:
        file(outputFile, 'wb').write(ppm.toText())
    else:
        nokiaFile.plain = ppm.toBinary()
        file(outputFile, 'wb').write(nokiaFile.encode())

if __name__ == "__main__":
    main()
