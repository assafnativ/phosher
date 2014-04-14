from struct import pack, unpack
from hashlib import sha1
execfile('xgold_parser.py')
execfile('ObjectWithStream.py')

IS_VERBOSE = False

def printIfVerbose(text):
    global IS_VERBOSE
    if IS_VERBOSE:
        print text


class Section(object):
    def __init__(self):
        pass
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
        printIfVerbose("Section %s at %x of %x bytes" % (self.name.replace('\x00', ' '), self.startPos, self.length))
        self.calcedChecksum = self.calcCheckSum(chunk.getRawData())
        if self.checksum != self.calcedChecksum:
            printIfVerbose("Checksum mismatch: %x <-> %x" % (self.checksum, self.calcedChecksum))
        self.subSections = []
        while chunk.tell() < (self.length - 4):
            subSection = SubSection()
            subSection.parseFromStream(chunk, self)
            self.subSections.append(subSection)

    def toBinary(self):
        if 'DUMFILE\x00' == self.version or 'LDB\x00' == self.name:
            return self.rawData
        result = ObjectWithStream()
        # Save place for checksum
        result.writeDword(0)
        # Save place for length
        result.writeDword(0)
        result.write(self.name[::-1])
        result.write(self.version)
        for subSection in self.subSections:
            result.write(subSection.toBinary())
        length = result.tell()
        result.seek(4,0)
        if self.length != length:
            print("! Section %s has changed its length (%x -> %x)" % (self.name, self.length, length))
        self.length = length
        result.writeDword(self.length)
        result.seek(4,0)
        rawData = result.readToEnd()
        result.seek(0, 0)
        result.writeDword(self.calcCheckSum(rawData))
        return result.getRawData()

class SubSection(object):
    def __init__(self):
        self.SECTIONS_PARSERS = {
                'TEXT':     self.parseText,
                'EDIT' :    self.parseEdit,
                'AORD' :    self.parseAord,
                'LDB\x00' : self.parseLdb,
                'ANIM' :    self.parseAnim,
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
                'ANIM' :    self.buildAnim,
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
        self.sectionId = stream.readDword()
        if 0 == self.sectionId:
            self.raw = stream.readToEnd()
            return
        self.length, subSection = readLTVChunk(stream, prefetchedBytes=4)
        self.name = subSection.read(4)
        self.flags = []
        self.flags.append(subSection.readByte())
        self.flags.append(subSection.readByte())
        self.flags.append(subSection.readByte())
        self.flags.append(subSection.readByte())
        self.stream = subSection
        #printIfVerbose("\tSub (%x) section %s at %x of %s bytes" % (self.sectionId, self.name, self.startPos, self.length))
        sectionType = self.parent.name
        if sectionType in self.SECTIONS_PARSERS:
            self.SECTIONS_PARSERS[sectionType]()
        else:
            print("Unknown section type %s" % repr(sectionType))

    def toBinary(self):
        result = ObjectWithStream()
        result.writeDword(self.sectionId)
        if 0 == self.sectionId:
            result.write(self.raw)
            return result.getRawData()
        # Save place for the length
        result.writeDword(0)
        result.write(self.name)
        for flag in self.flags:
            result.writeByte(flag)
        sectionType = self.parent.name
        if sectionType in self.SECTIONS_BUILDER:
            result.write(self.SECTIONS_BUILDER[sectionType]())
        else:
            raise Exception("Don't know how to build section of type %s" % sectionType)
        if result.tell() != self.length:
            printIfVerbose("! Section %s of type %s has changed its length (%x -> %x)" % (self.name, sectionType, self.length, result.tell()))
        self.length = result.tell()
        result.seek(4, 0)
        result.writeDword(self.length)
        return result.getRawData()

    def parseAnim(self):
        result = []
        stream = self.stream
        if 0 == self.sectionId:
            self.raw = stream.readToEnd()
            return
        self.numEntries = stream.readDword()
        animationsInfo = []
        for i in range(self.numEntries):
            animationIndex  = stream.readWord()
            animationUnk    = stream.readWord()
            animationOffset = stream.readDword()
            animationUnk2   = stream.readDword()
            animationsInfo.append((
                    animationIndex,
                    animationUnk,
                    animationOffset,
                    animationUnk2))
        self.animations = []
        lastIndex, lastUnk, startOffset, lastUnk2 = animationsInfo[0]
        for index, unk, endOffset, unk2 in animationsInfo[1:]:
            data = stream.read(endOffset - startOffset)
            self.animations.append((lastIndex, lastUnk, lastUnk2, data))
            startOffset = endOffset
            lastIndex = index
            lastUnk = unk
            lastUnk2 = unk2
        # Add last one
        data = stream.readToEnd()
        self.animations.append((index, unk, unk2, data))

    def buildAnim(self):
        if 0 == self.sectionId:
            return self.raw
        result = ObjectWithStream()
        result.writeDword(len(self.animations))
        totalLength = 0
        for index, unk, unk2, data in self.animations:
            result.writeWord(index)
            result.writeWord(unk)
            result.writeDword(totalLength)
            result.writeDword(unk2)
            totalLength += len(data)
        for index, unk, unk2, data in self.animations:
            result.write(data)
        return result.getRawData()

    def parseText(self):
        #printIfVerbose("\t\tParsing TEXT section subSection %s" % self.name)
        result = []
        stream = self.stream
        flags = self.flags
        if 0 == self.sectionId:
            self.raw = stream.readToEnd()
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
        numItems = stream.readWord()
        lengths = []
        for i in range(numItems):
            if self.isTwoBytesLen:
                entryLength = stream.readWord()
            else:
                entryLength = stream.readByte()
            if 0xfeff <= entryLength:
                raise Exception("Length error")
            if self.isUTF16:
                entryLength *= 2
            lengths.append(entryLength)
        texts = []
        for i, length in enumerate(lengths):
            newString = stream.read(length)
            if self.isUTF16:
                #printIfVerbose('\t\t\t%x %s' % (stream.tell(), newString.decode('UTF16')))
                pass
            else:
                #printIfVerbose('\t\t\t%x %s' % (stream.tell(), newString))
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
        result.writeWord(len(self.texts))
        for text in self.texts:
            textLen = len(text)
            if self.isUTF16:
                textLen /= 2
            if self.isTwoBytesLen:
                result.writeWord(textLen)
            else:
                result.writeByte(textLen)
        for text in self.texts:
            result.write(text)
        return result.getRawData()

    def buildText(self):
        if 0 == self.sectionId:
            return self.raw
        if 0 == self.compression:
            return self.buildTextNotCompressed()
        else:
            return self.raw

    def parseEdit(self):
        self.raw = self.stream.readToEnd()
    def parseAord(self):
        self.raw = self.stream.readToEnd()
    def parseLdb(self):
        self.raw = self.stream.readToEnd()
    def parseTone(self):
        self.raw = self.stream.readToEnd()
    def parseVfnt(self):
        self.raw = self.stream.readToEnd()
    def parsePlmn(self):
        self.raw = self.stream.readToEnd()
    def parseLpcs(self):
        self.raw = self.stream.readToEnd()
    def parseGsmc(self):
        self.raw = self.stream.readToEnd()
    def parsePale(self):
        self.raw = self.stream.readToEnd()
    def parseSchm(self):
        self.raw = self.stream.readToEnd()
    def parseThem(self):
        self.raw = self.stream.readToEnd()

    def buildEdit(self):
        return(self.raw)
    def buildAord(self):
        return(self.raw)
    def buildLdb(self):
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
    length  = stream.readDword()
    subSection = ObjectWithStream()
    subSectionData = stream.read(length - 4 - prefetchedBytes)
    subSection.writeDword(length)
    subSection.writeData(subSectionData)
    subSection.seek(4, 0)
    return (length, subSection)

def readCLTVChunk(stream):
    checksum = stream.readDword()
    length, subSection = readLTVChunk(stream, prefetchedBytes=4)
    return (checksum, length, subSection)

class PPM(object):
    def ppmFromXGold(self, data):
        version = unpack('>H', data[0x46:0x48])[0]
        blobs = parseXGoldPack(data)
        blobC = None
        # Get the longest C type blob
        for blobIndex, blob in enumerate(blobs):
            if blob[0] == 0xc:
                if None != blobC:
                    if len(blob[1]) > len(blobC):
                        blobC = blob[1]
                        blobCIndex = blobIndex
                else:
                    blobC = blob[1]
                    blobCIndex = blobIndex
        if None == blobC:
            raise Exception("Can't find the right blobC")
        rawData = blobC
        ppmStart = rawData.find('\x00MPP')
        if -1 == ppmStart or 0x10000 < ppmStart:
            raise Exception("Can't find PPM start")
        preData = rawData[:ppmStart]
        return (blobCIndex, blobs, preData, version), rawData[ppmStart:]

    def buildXGoldPPM(self, data):
        blobCIndex, blobs, preData, version = self.containerData
        newBlob = ObjectWithStream()
        newBlob.write(preData[:0x224])
        newBlob.writeDword(len(data))
        digest = sha1(data).digest()
        digestRevEndian = ""
        for i in range(0, len(digest), 4):
            digestRevEndian += digest[i:i+4][::-1]
        newBlob.write(digestRevEndian)
        newBlob.write(preData[0x23c:])
        newBlob.write(data)
        blobs[blobCIndex] = (0xc, newBlob.getRawData())
        return makeXGoldPack(blobs, version)

    def buildBB5PPM(self, data):
        raise Exception("Not implemented")

    def ppmFromBB5(self, data):
        ppmStart = data.find('\x00MPP')
        if -1 == ppmStart or 0x10000 < ppmStart:
            raise Exception("Can't find PPM start")
        preData = data[:ppmStart]
        return (data[:ppmStart], preData), data[ppmStart:]

    def __init__(self, ppm=None):
        self.CONTAINERS = {
                'XGold' : (self.ppmFromXGold, self.buildXGoldPPM),
                'BB5'   : (self.ppmFromBB5, self.buildBB5PPM) }
        self.DEFAULT_CONTAINER = 'XGold'
        if None != ppm:
            self.parsePPM(ppm)

    def dumpAnimationsToDisk(self, outputDir):
        if not os.path.isdir(outputDir):
            os.mkdir(outputDir)
            if not os.path.isdir(outputDir):
                raise Exception("Invalid output path")
        for section in self.sections:
            if 'ANIM' == section.name:
                for subSection in section.subSections:
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

    def parsePPM(self, ppm, containerType=None):
        if None == containerType:
            containerType = self.DEFAULT_CONTAINER
        if len(ppm) < 0x100:
            ppm = file(ppm, 'rb').read()
        if containerType not in self.CONTAINERS:
            raise Exception("Container %s not supported" % containerType)
        self.containerData, self.ppmData = self.CONTAINERS[containerType][0](ppm)
        return self.parsePPMData(self.ppmData)

    def parsePPMData(self, ppm):
        if len(ppm) < 0x100:
            ppm = file(ppm, 'rb').read()
        self.ppmLength = len(ppm)
        self.data = ObjectWithStream(ppm)
        if '\x00MPP' != self.data.read(4):
            raise Exception("Invalid magic in PPM header")
        self.version = self.data.readString()
        printIfVerbose("PPM version: %s" % self.version)
        self.data.seek(0x40, 0)
        self.langId = self.data.read(4)
        printIfVerbose("PPM lang ID: %s" % self.langId.replace('\x00', ''))
        self.sections = []
        while True:
            newSection = Section()
            newSection.parseFromStream(self.data)
            self.sections.append(newSection)
            if newSection.version == 'DUMFILE\x00':
                break

    def toBinary(self, containerType=None):
        if None == containerType:
            containerType = self.DEFAULT_CONTAINER
        result = ObjectWithStream()

        result.write('\x00MPP')
        result.write(self.version + '\x00')
        while result.tell() < 0x40:
            result.write('\xff')
        result.write(self.langId)
        for section in self.sections:
            result.write(section.toBinary())
        
        return result.getRawData()

    def make(self, outputFile, containerType=None):
        ppm = self.toBinary(containerType=containerType)
        ppm = self.CONTAINERS[containerType][1](ppm)
        file(outputFile, 'wb').write(ppm)

