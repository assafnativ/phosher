
from ..general.objectWithStream import *

from struct import pack, unpack
import time
import copy
import os

PADDING_TYPE_NO_PADDING = 0
PADDING_TYPE_DCT4 = 1
PADDING_TYPE_NEW  = 2

def attributesToStr(x):
    result = ''
    if x & 1:
        result += 'READ '
    if x & 2:
        result += 'HIDDEN '
    if x & 4:
        result += 'SYSTEM '
    if x & 8:
        result += 'VOLUME_ID '
    if x & 0x10:
        result += 'DIRECTORY '
    if x & 0x20:
        result += 'ARCHIVE '
    if x & 0x40:
        result += 'NOKIA '
    return result.strip()

def parseFileTime(x, micro=0):
    s = (x & 0x1f) * 2 + micro;    x >>= 5
    m = (x & 0x3f);        x >>= 6
    h = (x & 0x1f);        x >>= 5
    return (s, m, h)
def parseFileDate(x):
    d = (x & 0x7f);        x >>= 7
    m = (x & 0x0f);        x >>= 4
    y = (x & 0x1f) + 1980; x >>= 5
    return (d, m, y)

CLUSTER_CHAIN_END   = 0xffff
CLUSTER_BAD         = 0xfff7
CLUSTER_RESERVED    = 0x0001
CLUSTER_AVAILABLE   = 0x0000
def clusterType(x):
    if CLUSTER_AVAILABLE == x:
        return 'Available'
    elif CLUSTER_RESERVED == x:
        return 'Reserved'
    elif CLUSTER_RESERVED < x and x < CLUSTER_BAD:
        return 'UserData'
    elif CLUSTER_BAD == x:
        return 'BadCluster'
    elif CLUSTER_BAD < x and x < CLUSTER_CHAIN_END:
        return 'EndMarker'
    elif CLUSTER_CHAIN_END == x:
        return 'ChainEnd'

class LongFileNameEntry(ObjectWithStream):
    def __init__(self, stream):
        self.stream = stream
        self.partIndex      = self.readUInt8()      #  0
        self.name           = self.read(0x0a)     #  1
        self.attribs        = self.readUInt16()      # 11
        self.checksum       = self.readUInt8()      # 13
        self.name          += self.read(0x0c)     # 14
        self.zero           = self.readUInt16()      # 26
        self.name          += self.read(4)        # 28
        # Total 32

class DirEntry(ObjectWithStream):
    def __init__(self, stream, longName=None, parent=None):
        if hasattr(stream, 'read'):
            self.stream = stream
            self.longName = longName
            self.name           = self.read(8)        #  0
            self.ext            = self.read(3)        #  8
            self.attributes     = self.readUInt8()      # 11
            self.longFileName   = self.readUInt8()      # 12
            self.creationMicro  = self.readUInt8()      # 13
            self.creationTime   = self.readUInt16()      # 14
            self.creationDate   = self.readUInt16()      # 16
            self.accessDate     = self.readUInt16()      # 18
            self.zero           = self.read(2)        # 20
            self.updateTime     = self.readUInt16()      # 22
            self.updateDate     = self.readUInt16()      # 24
            self.firstCluster   = self.readUInt16()      # 26
            self.fileSize       = self.readUInt32()     # 28
            # Total 32
        else:
            info = stream
            self.longName = longName
            self.name           = info[ 0]
            self.ext            = info[ 1]
            self.attributes     = info[ 2]
            self.longFileName   = 0
            self.creationMicro  = info[ 3]
            self.creationTime   = info[ 4]
            self.creationDate   = info[ 5]
            self.accessDate     = info[ 6]
            self.zero           = '\x00\x00'
            self.updateTime     = info[ 7]
            self.updateDate     = info[ 8]
            self.firstCluster   = info[ 9]
            self.fileSize       = info[10]
        if self.isDir():
            self.content = []
        else:
            self.rawData = ""
        self.parent = parent
        self.parentCluster = None

    def __repr__(self):
        if self.name.startswith('\x00'):
            return "No file"
        result = ""
        result += ("%s (%s.%s)\n" % (self.longName, self.name, self.ext))
        result += ("Attributes: 0x%x\n" % (self.attributes))
        result += ("Reserved: 0x%x\n" % self.longFileName)
        result += ("Creation time: %s\n" % (repr(parseFileTime(self.creationTime, self.creationMicro))))
        result += ("Creation date: %s\n" % (repr(parseFileDate(self.creationDate))))
        result += ("Last access:   %s\n" % (repr(parseFileDate(self.accessDate))))
        result += ("Zero %s\n" % self.zero.encode('hex'))
        result += ("Modify time:   %s\n" % (repr(parseFileTime(self.updateTime))))
        result += ("Modify date:   %s\n" % (repr(parseFileDate(self.updateDate))))
        result += ("First cluster: 0x%x\n" % self.firstCluster)
        result += ("File size: 0x%x\n" % self.fileSize)
        return result

    def toRaw(self):
        if not self.isDir():
            raise Exception("This function is for folders only")
        if None != self.parentCluster and None == self.parent:
            raise Exception("Parent folder not set yet")
        if self.isLink():
            raise Exception("Trying to serialize a link")
        folderData = ObjectWithStream()
        if 0xff != self.attributes:
            # Add . and ..
            folderData.write(self.makeDotEntry())
            folderData.write(self.makeDotDotEntry())
        for f in self.content:
            if f.getName() in ['.', '..']:
                raise Exception(". and .. were supposed to be filltered out")
            longName = f.longName
            longNameEntry = f.makeLongNameEntry()
            if None != longNameEntry:
                folderData.write(longNameEntry)
            folderData.write(f.makeEntry())
        folderData.seek(0)
        return folderData.read()

    def updateData(self, data):
        if self.isDir():
            raise Exception("Folder has no data")
        self.rawData = data
        self.fileSize = len(data)

    def updateContent(self, content):
        if not self.isDir():
            raise Exception("File has no content")
        if 0 != self.fileSize:
            raise Exception("How the fuck that happned?!")
        if isinstance(content, DirEntry):
            self.content = content
        elif not isinstance(content, list):
            raise Exception("Input error")
        else:
            self.content = content[:]

    def makeLongNameEntry(self):
        if None == self.longName:
            return None
        result = ''
        longName = self.longName
        if 0 != (len(longName) % 26):
            longName += '\x00\x00'
        if 0 != (len(longName) % 26):
            longName += '\xff' * (26 - (len(longName) % 26))
        neededEntries = len(longName) // 26
        for i in range(neededEntries):
            pos = (neededEntries - i - 1) * 26
            indexByte = neededEntries - i
            if 0 == i:
                indexByte |= 0x40
            result += chr(indexByte)
            result += longName[pos:pos+10]
            pos += 10
            result += '\x0f\x00'
            result += chr(self.calcDosNameChecksum())
            result += longName[pos:pos+12]
            pos += 12
            result += '\x00\x00'
            result += longName[pos:pos+4]
        return result

    def makeEntry(self):
        result = ''
        name = self.name
        if len(name) < 8:
            name += ' ' * (8 - len(name))
        result += name
        ext = self.ext
        if len(ext) < 3:
            ext += ' ' * (3 - len(ext))
        result += ext
        result += chr(self.attributes)
        result += self.makeUInt8(self.longFileName)
        result += self.makeUInt8(self.creationMicro)
        result += self.makeUInt16(self.creationTime)
        result += self.makeUInt16(self.creationDate)
        result += self.makeUInt16(self.accessDate)
        result += self.zero
        result += self.makeUInt16(self.updateTime)
        result += self.makeUInt16(self.updateDate)
        result += self.makeUInt16(self.firstCluster)
        result += self.makeUInt32(self.fileSize)
        return result

    def makeDotEntry(self):
        result = '.          '
        result += chr(self.attributes)
        result += '\x00'
        result += self.makeUInt8(self.creationMicro)
        result += self.makeUInt16(self.creationTime)
        result += self.makeUInt16(self.creationDate)
        result += self.makeUInt16(self.accessDate)
        result += self.zero
        result += self.makeUInt16(self.updateTime)
        result += self.makeUInt16(self.updateDate)
        result += self.makeUInt16(self.firstCluster)
        result += self.makeUInt32(self.fileSize)
        return result

    def makeDotDotEntry(self):
        if None == self.parent:
            raise Exception("Dir %s had no parent!" % self.name)
        result = '..         '
        result += chr(self.parent.attributes)
        result += '\x00'
        result += self.makeUInt8(self.parent.creationMicro)
        result += self.makeUInt16(self.parent.creationTime)
        result += self.makeUInt16(self.parent.creationDate)
        result += self.makeUInt16(self.parent.accessDate)
        result += self.zero
        result += self.makeUInt16(self.parent.updateTime)
        result += self.makeUInt16(self.parent.updateDate)
        result += self.makeUInt16(max([0, self.parent.firstCluster]))
        result += self.makeUInt32(self.parent.fileSize)
        return result

    def calcDosNameChecksum(self):
        name = self.name
        if not isinstance(name, str):
            raise Exception("Name is not string, WTF?! %s" % (repr(name)))
        if len(name) < 8:
            name += ' ' * (8 - len(name))
        name += self.ext
        if len(name) < 11:
            name += ' ' * (11 - len(name))
        result = 0
        for c in map(ord, name):
            carry = result & 1
            result >>= 1
            result &= 0xff
            if carry:
                result |= 0x80
            result += c
            result &= 0xff
        return result

    def getName(self):
        if '' != self.longName:
            try:
                return (self.longName).decode('UTF-16LE').encode('cp1255').strip()
            except UnicodeEncodeError, e:
                return "InvalidName_%s" % (self.longName.encode('hex'))
        return self.name.strip()

    def isRootDir(self):
        return (0xff == self.attributes)
         
    def isDir(self):
        return (0 != (self.attributes & 0x10))

    def isLink(self):
        if not hasattr(self, "content"):
            return False
        if isinstance(self.content, DirEntry):
            return True
        return False

def parseImage(data, isVerbose=False):
    return FAT16(data, isVerbose=isVerbose)

class FAT16(ObjectWithStream):
    DCT4_NEW_CHUNK_HEADER    = 'f0f00001ff000000'.decode('hex')
    DCT4_LAST_CHUNK_HEADER   = 'f0f00001ffc00000'.decode('hex')
    DCT4_EMPTY_CHUNK_HEADER  = 'ffffffffffffffff'.decode('hex')
    DCT4_CHUNK_FOOTER        = 'fffffffffffffffffffffffffffffffffffffffffffff0f0'.decode('hex')
    DCT4_SECTOR_HEADER       = 'fff0ffff'.decode('hex')
    #DCT4_SECTOR_LENGTH       = 0x200
    DCT4_EMPTY_SECTOR        = '\xff' * 0x200
    DCT4_EMPTY_SECTOR_HEADER = '\xff' * 0x4
    DCT4_SECTORS_PER_CHUNK   = 0xfc

    def removeDCT4Padding(self):
        stream1 = ObjectWithStream()
        stream2 = ObjectWithStream()
        self.seek(0, 0)
        dataLength = len(self)
        sectorsCount = 0
        while self.tell() < dataLength:
            chunkHeader = self.read(8)
            if self.DCT4_LAST_CHUNK_HEADER == chunkHeader:
                isLastChunk = True
                pass
            elif self.DCT4_NEW_CHUNK_HEADER == chunkHeader:
                isLastChunk = False
                pass
            elif isLastChunk and self.DCT4_EMPTY_CHUNK_HEADER != chunkHeader:
                raise Exception("Invalid chunk in DCT4 Image")
            for i in range(self.DCT4_SECTORS_PER_CHUNK):
                if self.tell() >= dataLength:
                    break
                header = self.read(0x4)
                if header.startswith(self.DCT4_SECTOR_HEADER):
                    if header != self.DCT4_SECTOR_HEADER:
                        raise Exception("Invalid DCT4 image padding")
                    sectorId = unpack('>L', self.read(0x4))[0]
                    if sectorId != sectorsCount:
                        raise Exception("Out of sync - DCT4 image")
                    sectorId += 1
                    stream1.write(self.read(0x200))
                    stream2.write(header)
                elif header.startswith(self.DCT4_EMPTY_SECTOR_HEADER):
                    emptySector = self.read(0x200)
                    if (self.DCT4_EMPTY_SECTOR != emptySector) and (len(emptySector) == len(self.DCT4_EMPTY_SECTOR)):
                        raise Exception("Invalid DCT4 image padding")
                    stream2.write(header)
                else:
                    raise Exception("Invalid DCT4 image padding")
                sectorsCount += 1
            chunkFooter = self.read(0x18)
            if not isLastChunk and self.DCT4_CHUNK_FOOTER != chunkFooter:
                raise Exception("Wrong chunk footer")
        stream1.seek(0, 0)
        stream2.seek(0, 0)
        return (stream1, stream2)

    def addDCT4Padding(self, data):
        output = ObjectWithStream()
        dataLength = len(data)
        sectorId = 0
        while dataLength < data.tell():
            if data.tell() >= (dataLength - self.DCT4_CHUNK_LENGTH):
                output.write(self.DCT4_LAST_CHUNK_HEADER)
            else:
                output.write(self.DCT4_NEW_CHUNK_HEADER)
            for i in range(0xfc):
                if data.tell() < dataLength:
                    output.write(self.DCT4_SECTOR_HEADER)
                    output.write(pack('>L', sectorId))
                    sectorId += 1
                    sector = data.read(0x200)
                    if len(sector) < 0x200:
                        sector += '\xff' * (0x200 - len(sector))
                    output.write(sector)
                else:
                    output.write(self.DCT4_EMPTY_SECTOR_HEADER)
                    output.write(self.DCT4_EMPTY_SECTOR)
            output.write(self.DCT4_CHUNK_FOOTER)
        output.seek(0, 0)
        return output

    def removeNewPadding(self):
        stream1 = ObjectWithStream()
        stream2 = ObjectWithStream()
        self.seek(0, 0)
        dataLength = len(self)
        paddingChunkSize = (self.numPeddingLines + 4) * 0x10
        while self.tell() < dataLength:
            stream1.write(self.read(0xf800))
            stream2.write(self.read(paddingChunkSize))
        stream1.seek(0,0)
        stream2.seek(0,0)
        return (stream1, stream2)

    def addNewPadding(self, stream):
        output = ObjectWithStream()
        d = stream.read(0xf800)
        line = 0
        lineLength = 0xf800 / self.numPeddingLines
        while d != '':
            chunk_length = len(d)
            if len(d) < 0xf800:
                d += '\xff' * (0xf800 - len(d))
            output.write(d)
            for i in range(chunk_length // lineLength):
                output.write(pack('<L', line))
                output.write('\xff\x00')
                output.write('\xff' * 10)
                line += 1
            for i in range(self.numPeddingLines - (chunk_length // lineLength)):
                output.write('\xff' * 32)
            output.write('\xff' * 32)
            output.write('\xff\xff\x00\xff')
            output.write('\xff' * 12)
            output.write('\xf0\xf0\x03\x00\x00\x00\xf0\xf0')
            output.write('\xff' * 8)
            d = stream.read(0xf800)
        output.seek(0, 0)
        return output

    def guessPaddingType(self):
        if 'F0F00001FF000000FFF0FFFF00000000'.decode('hex') == self.peek(0x10):
            self.printIfVerbos("Using new DCT4 padding")
            return PADDING_TYPE_DCT4
        self.seek(0xf800)
        if '00000000FF00FFFFFFFFFFFFFFFFFFFF'.decode('hex') == self.peek(0x10):
            self.printIfVerbos("Using new type of padding")
            numLines = 0
            lineIndex = self.readUInt32()
            while lineIndex == numLines:
                numLines += 1
                self.read(0xc)
                lineIndex = self.readUInt32()
            self.numPeddingLines = numLines
            return PADDING_TYPE_NEW
        self.printIfVerbos("No padding")
        return PADDING_TYPE_NO_PADDING

    def __init__(self, data, isVerbose=False):
        self.isVerbose = isVerbose
        if len(data) < 0x100:
            self.stream  = file(data, 'rb')
        else:
            self.stream = ObjectWithStream()
            self.stream.write(data)
        self.seek(0, 0)
        self.paddingType = self.guessPaddingType()
        self.seek(0, 0)
        if self.paddingType == PADDING_TYPE_NEW:
            self.stream1, self.stream2 = self.removeNewPadding()
            self.stream = self.stream1
            self.seek(0, 0)
        elif self.paddingType == PADDING_TYPE_DCT4:
            self.stream1, self.stream2 = self.removeDCT4Padding()
            self.stream = self.stream1
            self.seek(0, 0)

        if '\xeb\xfe' != self.peek(2):
            raise Exception("Data doesn't seem like FAT16")
        self.clustersToFilesDic = {}
        self.parseHeaders()
        if (self.bytesPerSector - self.tell()) > 0:
            self.bootSecPadding = self.read(self.bytesPerSector - self.tell())
        else:
            self.bootSecPadding = ''
        self.bytesPerCluster = self.bytesPerSector * self.sectorsPerCluster
        #self.reservedSectors = self.read(self.reserverSectorsCount * self.bytesPerSector)
        # Parse the FAT
        self.printIfVerbos("Data starts at 0x%x" % self.tell())
        if 2 != self.numOfTables:
            self.printIfVerbos("More than two tables stop parsing")
            return
        self.tables = []
        for i in range(self.numOfTables):
            self.printIfVerbos("Table %d starts at 0x%x" % (i, self.tell()))
            tableData = self.read(self.sectorsPerFAT * self.bytesPerSector)
            table = unpack('<' + ('H' * (len(tableData) / 2)), tableData)
            table = list(table)
            if 0 != (self.tell() % self.bytesPerSector):
                print("! VTable padding error")
            self.tables.append(table)
        if self.tables[0] != self.tables[1]:
            #raise Exception("! The two FATs do not match")
            print("! The two FATs do not match, using the first one")
        self.table = self.tables[0]
        # Parse root dir
        self.printIfVerbos("Root dir starts at 0x%x" % self.tell())
        self._rootDirStart = self.tell()
        self._rootDirSize  = self.maxRootEntries * 0x20
        self._rootDirData = self.read(self._rootDirSize)
        self.rootDir = DirEntry( \
                ( \
                    '/',
                    '   ',
                    0xff, # Special attributes for root dir
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    -1,
                    0), '/')
        content = self._parseDirAndUpdateParent(self._rootDirData, self.rootDir)
        self.rootDir.updateContent(content)
        if 0 != (self.tell() % self.bytesPerSector):
            self.rootDirPadding = self.read(abs(self.tell() % (-self.bytesPerSector)))
        else:
            self.rootDirPadding = ''
        self.dataStart = self.tell()
        self.firstDataSector = self.dataStart // self.bytesPerSector
        self.clustersToFilesDic[0] = self.rootDir
        self.printIfVerbos("Files data starts at: 0x%x" % self.dataStart)
        self._readFilesRecursively(self.rootDir)
        self._resolveParents(self.rootDir)

    def makeNewTable(self):
        raise Exception("Not implemented")
        tableEntries = (self.sectorsPerFAT * self.bytesPerSector) // 2
        table = [0] * tableEntries
        table[0] = 0xfff8
        table[1] = 0xff7f

    def _obtainNextFreeCluster(self):
        newCluster = self._getNextFreeCluster()
        self.eraseCluster(newCluster)
        self.table[newCluster] = CLUSTER_CHAIN_END
        return newCluster

    def _getNextFreeCluster(self):
        return self.table.index(CLUSTER_AVAILABLE)

    def eraseCluster(self, cluster):
        self._writeCluster(cluster, '\x00' * self.bytesPerCluster)
        self.table[cluster] = 0

    def _writeCluster(self, cluster, data):
        if len(data) > self.bytesPerCluster:
            raise Exception("No room for data in cluster")
        elif len(data) < self.bytesPerCluster:
            data += '\x00' * (self.bytesPerCluster - len(data))
        clusterOffset = self._getClusterOffset(cluster)
        self.seek(clusterOffset, 0)
        self.write(data)

    def _writeRoot(self, data):
        if len(data) > self._rootDirSize:
            raise Exception("No room for data in root dir")
        elif len(data) < self._rootDirSize:
            data += '\x00' * (self.bytesPerCluster - len(data))
        self.seek(self._rootDirStart, 0)
        self.write(data)
        self._rootDirData = data

    def readFile(self, path):
        fileObj = self.getFileObj(path)
        if None == fileObj:
            raise Exception("Can't find file %s" % path)
        if fileObj.isDir():
            raise Exception("Path is directory")
        return fileObj.rawData

    def makeShortName(self, fname, directory=None):
        content = directory.content
        index = 0
        extPos = fname.rfind('.')
        if -1 == extPos:
            ext = '   '
        else:
            ext = fname[extPos+1:extPos+4]
            if len(ext) < 3:
                ext += ' ' * (3 - len(ext))
            ext = ext.upper()
        if extPos != -1 and extPos < 6:
            fnameTemplate = fname[:extPos]
            fnameTemplate += ' ' * (6 - len(fnameTemplate))
        else:
            fnameTemplate = fname[:6]
            if len(fnameTemplate) < 6:
                fnameTemplate += ' ' * (6 - len(fnameTemplate))
            fnameTemplate = fnameTemplate.upper()
        fnameTemplate += '~%s'
        for i in ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P']:
            nameToCheck = fnameTemplate % i
            found = False
            if None != directory:
                for f in content:
                    if f.name == nameToCheck:
                        found = True
            if False == found:
                return ((fnameTemplate % i), ext)
        raise Exception("Failed to create short name for %s" % fname)

    def splitFullPath(self, fullPath):
        fullPath = fullPath.replace('\\', '/')
        if fullPath[-1] == '/':
            fullPath = fullPath[:-1]
        pos = fullPath.rfind('/')
        if -1 == pos:
            fname = fullPath
            path = '/'
        else:
            fname = fullPath[pos+1:]
            path = fullPath[:pos]
        return path, fname, fullPath

    def nameToUnicode(self, name):
        return name.decode('cp1255').encode('utf-16LE')

    def createFile(self, fullPath, attrib=0x24, creationMicro=0, creationTime=0, creationDate=0, accessDate=0, updateTime=0, updateDate=0, firstCluster=None):
        if attrib & 0x10:
            raise Exception("Use mkdir to create dir")
        path, fname, fullPath = self.splitFullPath(fullPath)
        if path in ['/', '\\', '']:
            directory = self.rootDir
        else:
            directory = self.getFileObj(path)
        if None == directory:
            raise Exception("Can't find containing folder for %s" % path)
        shortName, ext = self.makeShortName(fname, directory)
        if None == firstCluster:
            firstCluster = self._obtainNextFreeCluster()
        uniName = self.nameToUnicode(fname)
        newFileEntry = self._newDirEntry( \
                ( \
                    shortName,
                    ext,
                    attrib,
                    creationMicro,
                    creationTime,
                    creationDate,
                    accessDate,
                    updateTime,
                    updateDate,
                    firstCluster,
                    0), uniName, '')
        self.addEntryToCluesterToFilesDic(firstCluster, newFileEntry)
        content = directory.content + [newFileEntry]
        self._updateFolder(path, content)
        return newFileEntry

    def addEntryToCluesterToFilesDic(self, clusterId, newEntry):
        if clusterId in self.clustersToFilesDic:
            currentFiles = self.clustersToFilesDic[clusterId]
            if isinstance(currentFiles, list):
                currentFiles.append(newEntry)
            else:
                self.clustersToFilesDic[clusterId] = [currentFiles, newEntry]
        else:
            self.clustersToFilesDic[clusterId] = newEntry

    def removeEnteryFromClusterToFilesDic(self, entry):
        clusterId = entry.firstCluster
        if not clusterId in self.clustersToFilesDic:
            raise Exception("Can't find file in dic")
        currentFiles = self.clustersToFilesDic[clusterId]
        if isinstance(currentFiles, list):
            currentFiles.remove(entry)
        else:
            del(self.clustersToFilesDic[clusterId])

    def createLinkToFile(self, fullPath, otherFile, prefixData=None, attrib=0x24, creationMicro=0, creationTime=0, creationDate=0, accessDate=0, updateTime=0, updateDate=0):
        otherObject = self.getFileObj(otherFile)
        firstCluster = otherObject.firstCluster
        newFileEntry = self.createFile(
                        fullPath, 
                        attrib=attrib, 
                        creationMicro=creationMicro, 
                        creationTime=creationTime, 
                        creationDate=creationDate, 
                        accessDate=accessDate, 
                        updateTime=updateTime, 
                        updateDate=updateDate )
        if None == prefixData:
            prefixData = ""
        else:
            if len(prefixData) % self.bytesPerCluster:
                prefixData += "\x00" * (self.bytesPerCluster - (len(prefixData) % self.bytesPerCluster))
        self.writeFile(fullPath, prefixData)
        
        clusters = self.getClustersChain(newFileEntry.firstCluster)
        # Make the link
        self.table[clusters[-1]] = otherObject.firstCluster
        newClusters = self.getClustersChain(newFileEntry.firstCluster)
        newSize = len(newClusters) * self.bytesPerCluster
        newFileEntry.fileSize = newSize

    def createLinkToDir(self, fullPath, otherPath, attrib=0x34, creationMicro=0, creationTime=0, creationDate=0, accessDate=0, updateTime=0, updateDate=0, firstCluster=None):
        otherObject = self.getFileObj(otherPath)
        if None == otherObject:
            raise Exception("Link target not found")
        firstCluster = otherObject.firstCluster
        print "Creating link from %s to %s" % (fullPath, otherPath)
        self.mkdir(
            fullPath, 
            content=otherObject,
            attrib=attrib, 
            creationMicro=creationMicro, 
            creationTime=creationTime, 
            creationDate=creationDate, 
            accessDate=accessDate, 
            updateTime=updateTime, 
            updateDate=updateDate, 
            firstCluster=firstCluster)

    def _deleteDirContent(self, path, dirObj):
        if not hasattr(dirObj, 'content'):
            print "Parsing error! the folder %s %s has no content" % (path, dirObj.getName())
            return
        content = [x.getName() for x in dirObj.content]
        for subFile in content:
            if subFile not in ['.', '..']:
                self.rmfile(path + '/' + subFile)

    def rmfile(self, fullPath):
        path, fname, fullPath = self.splitFullPath(fullPath)
        directory = self.getFileObj(path)
        if None == directory:
            raise Exception("Can't find directory %s for deleting of %s" % (path, fname))
        if '*' == fname:
            self._deleteDirContent(path, directory)
        else:
            for fileObj in directory.content:
                if fileObj.getName() == fname:
                    break
            else:
                raise Exception("File %s/%s not found" % (path, fname))
            if fileObj.isDir():
                # Recursivly delete all files in dir
                self._deleteDirContent(path + '/' + fname, fileObj)
            content = directory.content
            if fileObj not in content:
                raise Exception("File not found")
            content.remove(fileObj)
            clusters = self.getClustersChain(fileObj.firstCluster)
            for cluster in clusters:
                self.eraseCluster(cluster)
                self.table[cluster] = 0
            self.removeEnteryFromClusterToFilesDic(fileObj)
            self._updateFolder(path, content)

    def setAttributes(self, fullPath, newAttrib):
        path, fname, fullPath = self.splitFullPath(fullPath)
        fileObj = self.getFileObj(fullPath)
        if fileObj.isDir() and (0 == (0x10 & newAttrib)):
            raise Exception("Setting file attributes to folder")
        if not fileObj.isDir() and (0 != (0x10 & newAttrib)):
            raise Exception("Setting folder attributes to file")
        fileObj.attributes = newAttrib
        directory = self.getFileObj(path)
        if None == directory:
            raise Exception("Cant find dir: %s" % path)
        if not directory.isDir():
            raise Exception("Containing dir is not a dir?!")
        self._updateFolder(path, directory.content)

    def mkdir(self, fullPath, content=None, attrib=0x34, creationMicro=0, creationTime=0, creationDate=0, accessDate=0, updateTime=0, updateDate=0, firstCluster=None):
        if 0 == (0x10 & attrib):
            raise Exception("Attributes error, missing 0x10 from folder")
        if None == content:
            content = []
        path, dirName, fullPath = self.splitFullPath(fullPath)
        containingDir = self.getFileObj(path)
        shortName, ext = self.makeShortName(dirName, containingDir)
        uniName = self.nameToUnicode(dirName)
        if None == firstCluster:
            firstCluster = self._obtainNextFreeCluster()
            isALink = False
        else:
            if [] == content:
                raise Exception("Links not supposed to have content")
            isALink = True
        newDirEntry = self._newDirEntry( \
                ( \
                    shortName,
                    ext, 
                    attrib,
                    creationMicro,
                    creationTime,
                    creationDate,
                    accessDate,
                    updateTime,
                    updateDate,
                    firstCluster,
                    0), uniName, content, containingDir)
        self._updateFolder(path, containingDir.content + [newDirEntry])
        if not isALink:
            self._updateFolder(fullPath, content)
        return newDirEntry

    def _newDirEntry(self, info, longName, data, containingDir=None):
        firstCluster = info[9]
        if None == firstCluster:
            firstCluster = self._obtainNextFreeCluster()
        newDirEntry = DirEntry(info, longName, containingDir)
        if newDirEntry.isDir():
            newDirEntry.updateContent(data)
        else:
            newDirEntry.updateData(data)
        self.addEntryToCluesterToFilesDic(firstCluster, newDirEntry)
        return newDirEntry

    def _updateFolder(self, path, content):
        dirObj = self.getFileObj(path)
        if None == dirObj:
            raise Exception("Failed to find dir object for %s" % path)
        if not dirObj.isDir():
            raise Exception("Path is a file")
        if dirObj.isLink():
            raise Exception("Trying to update a link")
        dirObj.updateContent(content)
        if dirObj.isRootDir():
            self._writeRootDir()
        else:
            data = dirObj.toRaw()
            clusters = self._fixClustersChain(dirObj.firstCluster, len(data))
            for i, cluster in enumerate(clusters):
                self._writeCluster(cluster, data[i*self.bytesPerCluster:(i+1)*self.bytesPerCluster])

    def _fixClustersChain(self, firstCluster, neededBytes):
        clusters = self.getClustersChain(firstCluster)
        neededClusters = (neededBytes // self.bytesPerCluster) + 1
        while neededClusters > len(clusters):
            # Add new cluster to file
            newCluster = self._obtainNextFreeCluster()
            self.table[clusters[-1]] = newCluster
            clusters.append(newCluster)
        while neededClusters < len(clusters):
            # Remove a cluster from file
            self.eraseCluster(clusters[-1])
            clusters = clusters[:-1]
            self.table[clusters[-1]] = CLUSTER_CHAIN_END
        return clusters

    def writeFile(self, fullPath, data=None):
        if fullPath in ['\\', '/', '']:
            raise Exception("Error path is root dir")
        path, fname, fullPath = self.splitFullPath(fullPath)
        fileObj = self.getFileObj(fullPath)
        if None == fileObj:
            raise Exception("Path not found %s" % path)
        if fileObj.isDir():
            raise Exception("Path is directory %s" % path)
        oldData = fileObj.rawData
        fileObj.rawData = data
        fileObj.fileSize = len(data)
        clusters = self._fixClustersChain(fileObj.firstCluster, len(data))
        for i, cluster in enumerate(clusters):
            self._writeCluster(cluster, data[i*self.bytesPerCluster:(i+1)*self.bytesPerCluster])
        self._updateFolder(path, self.getFileObj(path).content)

    def _writeRootDir(self):
        data = self.rootDir.toRaw()
        self._writeRoot(data)

    def makeNoPadding(self):
        output = ObjectWithStream()
        header = ''
        header += self.jumpOpcode
        header += self.nopOpcode
        header += self.oemName
        header += self.makeUInt16(self.bytesPerSector)
        header += self.makeUInt8(self.sectorsPerCluster)
        header += self.makeUInt16(self.reserverSectorsCount)
        header += self.makeUInt8(self.numOfTables)
        header += self.makeUInt16(self.maxRootEntries)
        totalSectors = self.totalSectors
        if totalSectors < 0x10000:
            header += self.makeUInt16(totalSectors)
        else:
            header += self.makeUInt16(0)
        header += self.makeUInt8(self.mediaDescriptor)
        header += self.makeUInt16(self.sectorsPerFAT)
        header += self.makeUInt16(self.sectorsPerTrack)
        header += self.makeUInt16(self.numOfHeads)
        header += self.makeUInt32(self.hiddenSectors)
        if totalSectors >= 0x10000:
            header += self.makeUInt32(totalSectors)
        else:
            header += self.makeUInt32(totalSectors + self.hiddenSectors)
        # Extended BIOS parameter block
        header += self.makeUInt8(self.physicalDriveNum)
        header += self.makeUInt8(self.reserved)
        header += self.makeUInt8(self.extendedBootSig)
        header += self.makeUInt32(self.diskId)
        header += self.volumeLabel
        header += self.fatType
        header += self.bootCode
        header += self.makeUInt16(self.bootSectorSig)
        output.write(header)

        tableRaw = pack('<' + ('H' * len(self.table)), *self.table)
        for i in range(self.numOfTables):
            output.write(tableRaw)
        rootDirRawLength = self.maxRootEntries * 0x20
        if 0 != (rootDirRawLength % self.bytesPerSector):
            rootDirRawLength += (self.bytesPerSector - (rootDirRawLength % self.bytesPerSector))
        rootDirRaw = self.rootDir.toRaw()
        if len(rootDirRaw) < rootDirRawLength:
            rootDirRaw += '\x00' * (rootDirRawLength - len(rootDirRaw))
        output.write(rootDirRaw)

        self.seek(self.dataStart)
        output.write(self.read())

        output.seek(0, 0)
        return output.read()

    def make(self):
        output = ObjectWithStream(self.makeNoPadding())
        if self.paddingType == PADDING_TYPE_DCT4:
            output = self.addDCT4Padding(output)
        if self.paddingType == PADDING_TYPE_NEW:
            output = self.addNewPadding(output)
        output.seek(0, 0)
        return output.read()

    def readPadding(self, paddingLength):
        if 0 != paddingLength:
            paddingZero = self.read(paddingLength)
            if paddingZero.count('\x00') != paddingLength:
                raise Exception("Padded image error")

    def readModPadding(self, paddingMod=0x200):
        paddingLength = abs(self.tell() % (-paddingMod))
        if 0 != paddingLength:
            paddingZero = self.read(paddingLength)
            if paddingZero.count('\x00') != paddingLength:
                raise Exception("Padded image error")

    def getClustersChain(self, firstCluster):
        if 'EndMarker' == clusterType(firstCluster):
            raise Exception("Chain start error")
        if 'UserData' != clusterType(firstCluster):
            raise Exception("Bad cluster type")
        clusters = [firstCluster]
        if firstCluster > len(self.table):
            raise Exception("Fat table out of range 0x%x" % (firstCluster))
        nextCluster = self.table[firstCluster]
        while 'UserData' == clusterType(nextCluster):
            clusters.append(nextCluster)
            nextCluster = self.table[nextCluster]
        return clusters

    def readFileByCluster(self, firstCluster):
        rawData = None
        clusters = self.getClustersChain(firstCluster)
        if not isinstance(clusters, list):
            raise Exception("WTF")
        rawData = ''.join([self._readCluster(x) for x in clusters])
        return rawData

    def _readFilesRecursively(self, dirObj):
        directory = dirObj.content
        for f in directory:
            if '\xe5' == f.name[0]:
                # File is deleted
                continue
            if f.getName() in ['.', '..']:
                raise Exception("Dot and DotDot were supposed to be filtered out")
            entryData = self.readFileByCluster(f.firstCluster)
            if None != entryData:
                if f.isDir():
                    f.content = self._parseDirAndUpdateParent(entryData, f)
                    self._readFilesRecursively(f)
                    f.rawData = entryData
                else:
                    if len(entryData) < f.fileSize:
                        self.printIfVerbos("! Not all data for %s was read. Read %d bytes out of %d using clusters: %s" % (f.getName(), len(entryData), f.fileSize, repr(self.getClustersChain(f.firstCluster))))
                    f.rawData = entryData[:f.fileSize]
                    f.parent = dirObj
            else:
                if f.isDir():
                    f.content = []
                else:
                    f.rawData = ''

    def _getClusterOffset(self, x):
        return self.dataStart + ((x - 2) * self.bytesPerCluster)
                
    def _readCluster(self, x):
        clusterOffset = self._getClusterOffset(x)
        self.seek(clusterOffset, 0)
        return self.read(self.bytesPerCluster)

    def _resolveParents(self, dirObj):
        if not dirObj.isDir():
            return
        if '\xe5' == dirObj.name[0]:
            # Folder is deleted
            return
        if '/' != dirObj.name and None == dirObj.parent:
            if dirObj.parentCluster not in self.clustersToFilesDic:
                raise Exception("Can't resolve dirName for %s %s %s" % (dirObj.name, dirObj.getName(), repr(dirObj.parentCluster)))
            parent = self.clustersToFilesDic[dirObj.parentCluster]
            if isinstance(parent, list):
                parent = parent[0]
            dirObj.parent = parent
        content = dirObj.content
        for f in content:
            self._resolveParents(f)

    def _parseDirAndUpdateParent(self, dirData, dirObj):
        if isinstance(dirData, str):
            stream = ObjectWithStream(dirData)
        else:
            stream = dirData
        lastNameIndex = 0
        longName = ''
        result = []
        while True:
            entryType = stream.read(15)
            if 0 == len(entryType):
                break
            stream.seek(-15, 1)
            if '\x0f\x00' != entryType[-4:-2] and '\x00\x00\x00\x00' != entryType[-4:]:
                #self.printIfVerbos("File at 0x%x" % stream.tell())
                if '' != longName:
                    endPos = longName.find('\xff\xff')
                    if -1 != endPos:
                        longName = longName[:endPos]
                    longName = longName.replace('\x00\x00', '')
                dirEntry = DirEntry(stream, longName)
                if dirEntry.name[0] in ['\x00', '\xff', '\xe5', ' ']:
                    self.printIfVerbos( "File ?%s is deleted" % dirEntry.name[1:] )
                    if '' != longName:
                        self.printIfVerbos("It had long name of %s" % longName)
                elif dirEntry.getName() == '.':
                    pass
                elif dirEntry.getName() == '..':
                    #print "Found parent for %s" % dirObj.getName()
                    dirObj.parentCluster = dirEntry.firstCluster
                else:
                    if dirEntry.firstCluster in self.clustersToFilesDic:
                        #raise Exception("Double definition for dir %x %s" % (dirEntry.firstCluster, dirEntry.getName()))
                        print "Found link: %s" % dirEntry.getName()
                    self.addEntryToCluesterToFilesDic(dirEntry.firstCluster, dirEntry)
                    result.append(dirEntry)
                #self.printIfVerbos(repr(dirEntry))
                longName = ''
                lastNameIndex = 0
            elif '\x0f\x00' == entryType[-4:-2]:
                # Long file name
                lfn = LongFileNameEntry(stream)
                index = lfn.partIndex - 0x40
                if index > lastNameIndex:
                    if '' != longName:
                        self.printIfVerbos("! Long name not used %s (%x, %x) - Might be reminings of some deleted file" % (longName, index, lastNameIndex))
                    longName = ''
                longName = lfn.name + longName
            else:
                emptyEntry = stream.read(0x20)
        return result

    def ls(self, path=None, root=None):
        if None == root:
            root = self.rootDir
        if None != path and '' != path and path[0] in ['/', '\\']:
            path = path[1:]
        if '' == path or None == path:
            for i, f in enumerate(root):
                if f.isDir():
                    print '%4i [%s]' % (i, f.getName())
                else:
                    print '%4i %s %d' % (i, f.getName(), f.fileSize)
        else:
            pos = path.find('/')
            if -1 == pos:
                pos = path.find('\\')
                if -1 == pos:
                    pos = len(path)
            next_dir = path[:pos]
            path = path[pos:]
            for f in root:
                if f.getName() == next_dir:
                    self.ls(path, f.content)
                    break
            else:
                print "Path not found"

    def getFileObj(self, path, root=None):
        if None == root:
            root = self.rootDir.content
            if path in ['/', '\\', '']:
                return self.rootDir
        if '' != path and path[0] in ['/', '\\']:
            path = path[1:]
        pos = path.find('/')
        if -1 == pos:
            pos = path.find('\\')
            if -1 == pos:
                pos = len(path)
        next_dir = path[:pos]
        path = path[pos:]
        for f in root:
            if f.getName() == next_dir:
                if '' == path:
                    return f
                else:
                    return self.getFileObj(path, f.content)
        else:
            #print "Path not found"
            return None

    def printTree(self, start=None, path=None):
        if None == start:
            start = self.rootDir
        if None == path:
            path = '/'
        for f in start:
            if f.getName() in ['.', '..']:
                continue
            print path + f.getName()
            if f.isDir():
                self.printTree(f.content, path + f.getName() + '/')

    def dumpTree(self, outputPath, start=None, path=None):
        if outputPath[-1] not in ['/', '\\']:
            outputPath += '/'
        if not os.path.isdir(outputPath):
            os.mkdir(outputPath)
        if None == start:
            start = self.rootDir.content
        if None == path:
            path = '/'
        for f in start:
            if f.getName() in ['.', '..']:
                continue
            if f.isDir():
                new_path = path + f.getName()
                if new_path[-1] not in ['/', '\\']:
                    new_path += '/'
                os.mkdir(outputPath + new_path)
                self.dumpTree(outputPath, f.content, new_path)
            else:
                fname = outputPath + path + f.getName()
                print fname
                file(fname, 'wb').write(f.rawData)

    def printIfVerbos(self, text):
        if self.isVerbose:
            print text

    def parseHeaders(self):
        self.jumpOpcode      = self.read(2)            #   0
        self.nopOpcode       = self.read(1)            #   2
        self.oemName         = self.read(8)            #   3
        self.bytesPerSector  = self.readUInt16()       #  11
        self.sectorsPerCluster = self.readUInt8()      #  13
        self.reserverSectorsCount = self.readUInt16()  #  14
        self.numOfTables     = self.readUInt8()        #  16
        self.maxRootEntries  = self.readUInt16()       #  17
        self.totalSectors    = self.readUInt16()       #  19
        self.mediaDescriptor = self.readUInt8()        #  21
        self.sectorsPerFAT   = self.readUInt16()       #  22
        self.sectorsPerTrack = self.readUInt16()       #  24
        self.numOfHeads      = self.readUInt16()       #  26
        self.hiddenSectors   = self.readUInt32()       #  28
        if 0 == self.totalSectors:
            self.totalSectors    = self.readUInt32()   #  32
        else:
            self.extendedTotalSecotrs = self.readUInt32()
        if self.isVerbose:
            print 'Jump Opcode: ' + self.jumpOpcode.encode('hex')
            print 'NOP Opcode: ' + self.nopOpcode.encode('hex')
            print 'OEM name: ' + self.oemName
            print 'Bytes per sector (0x200): 0x%x' % self.bytesPerSector
            print 'Sectors per cluster (Supposed to be a power of 2): 0x%x' % self.sectorsPerCluster
            print 'Reserver sectors count (1 to 0x80): 0x%x' % self.reserverSectorsCount
            print 'Num of tables (2): 0x%x' % self.numOfTables
            print 'Max num of root dirs (224): 0x%x' % self.maxRootEntries
            print 'Total sectors (Zero is ok): 0x%x' % self.totalSectors
            print 'Media descriptor (0xF?): 0x%x' % self.mediaDescriptor
            print 'Sectors per FAT: 0x%x' % self.sectorsPerFAT
            print 'Sectors per track: 0x%x' % self.sectorsPerTrack
            print 'Number of heads: 0x%x' % self.numOfHeads
            print 'Hidden sectors: 0x%x' % self.hiddenSectors
            print 'Total sectors: 0x%x' % self.totalSectors

        # Extended BIOS parameter block
        self.printIfVerbos( '--- Extended BIOS parameter block ---')
        self.physicalDriveNum    = self.readUInt8()     #  36
        self.reserved            = self.readUInt8()     #  37
        self.extendedBootSig     = self.readUInt8()     #  38
        self.diskId              = self.readUInt32()    #  39
        self.volumeLabel         = self.read(11)      #  43
        self.fatType             = self.read(8)       #  54
        self.bootCode            = self.read(448)     #  62
        self.bootSectorSig       = self.readUInt16()
        if self.isVerbose:
            print 'Physical drive number (0 to 0x80): 0x%x' % self.physicalDriveNum
            print 'Reserved: 0x%x' % self.reserved
            print 'Extended boot signature: 0x%x' % self.extendedBootSig
            print 'ID: 0x%x' % self.diskId
            print 'Volume Label: ' + self.volumeLabel
            print 'Fat type: ' + self.fatType
            print 'Boot sector signature (0x55 0xAA): 0x%x' % self.bootSectorSig


# Data start = first_root_sec + size_root-dir
# Data start = reserved_sec + (nfat * bytesPerSector) + ((nroot * 32) / bytePerSector)

# XGold research
# Name              Supposed offset   XGold offset      Delta
# Cluster  0xa5          0xd6e00         0xd6e00            0
# Cluster  0xaa          0xdbe00         0xdbe00            0
# Cluster  0xd8         0x109e00        0x109e00            0
# Cluster 0x115         0x146e00        0x146e00            0
# 


# AF000 to AFE00 - Is all FFs
