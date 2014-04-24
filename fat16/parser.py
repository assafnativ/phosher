
from ..general.ObjectWithStream.py import *

from cStringIO import *
from struct import pack, unpack
import time
import copy

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
        self.partIndex      = self.readByte()      #  0
        self.name           = stream.read(0x0a)     #  1
        self.attribs        = self.readWord()      # 11
        self.checksum       = self.readByte()      # 13
        self.name          += stream.read(0x0c)     # 14
        self.zero           = self.readWord()      # 26
        self.name          += stream.read(4)        # 28
        # Total 32

class DirEntry(ObjectWithStream):
    def __init__(self, stream, longName=None, parent=None):
        if hasattr(stream, 'read'):
            self.stream = stream
            self.longName = longName
            self.name           = stream.read(8)        #  0
            self.ext            = stream.read(3)        #  8
            self.attributes     = self.readByte()      # 11
            self.longFileName   = self.readByte()      # 12
            self.creationMicro  = self.readByte()      # 13
            self.creationTime   = self.readWord()      # 14
            self.creationDate   = self.readWord()      # 16
            self.accessDate     = self.readWord()      # 18
            self.zero           = stream.read(2)        # 20
            self.updateTime     = self.readWord()      # 22
            self.updateDate     = self.readWord()      # 24
            self.firstCluster   = self.readWord()      # 26
            self.fileSize       = self.readDword()     # 28
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
        folderData = StringIO()
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
        result += self.makeByte(self.longFileName)
        result += self.makeByte(self.creationMicro)
        result += self.makeWord(self.creationTime)
        result += self.makeWord(self.creationDate)
        result += self.makeWord(self.accessDate)
        result += self.zero
        result += self.makeWord(self.updateTime)
        result += self.makeWord(self.updateDate)
        result += self.makeWord(self.firstCluster)
        result += self.makeDword(self.fileSize)
        return result

    def makeDotEntry(self):
        result = '.          '
        result += chr(self.attributes)
        result += '\x00'
        result += self.makeByte(self.creationMicro)
        result += self.makeWord(self.creationTime)
        result += self.makeWord(self.creationDate)
        result += self.makeWord(self.accessDate)
        result += self.zero
        result += self.makeWord(self.updateTime)
        result += self.makeWord(self.updateDate)
        result += self.makeWord(self.firstCluster)
        result += self.makeDword(self.fileSize)
        return result

    def makeDotDotEntry(self):
        if None == self.parent:
            raise Exception("Dir %s had no parent!" % self.name)
        result = '..         '
        result += chr(self.parent.attributes)
        result += '\x00'
        result += self.makeByte(self.parent.creationMicro)
        result += self.makeWord(self.parent.creationTime)
        result += self.makeWord(self.parent.creationDate)
        result += self.makeWord(self.parent.accessDate)
        result += self.zero
        result += self.makeWord(self.parent.updateTime)
        result += self.makeWord(self.parent.updateDate)
        result += self.makeWord(max([0, self.parent.firstCluster]))
        result += self.makeDword(self.parent.fileSize)
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
            return ('\xff\xfe' + self.longName).decode('UTF-16').encode('cp1255').strip()
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

def splitXGoldStream(data):
    stream1 = StringIO()
    stream2 = StringIO()
    parts = len(data) // 0x10000
    if 0 != (len(data) %  0x10000):
        parts += 1
    for i in range(parts):
        stream1.write(data[0x10000 * i          :0x10000 * i +  0xf800])
        stream2.write(data[0x10000 * i + 0xf800 :0x10000 * i + 0x10000])
    stream1.seek(0,0)
    stream2.seek(0,0)
    return (stream1, stream2)

def makePaddedImage(data):
    output = StringIO()
    stream = StringIO(data)
    d = stream.read(0xf800)
    line = 0
    while d != '':
        chunk_length = len(d)
        if len(d) < 0xf800:
            d += '\xff' * (0xf800 - len(d))
        output.write(d)
        for i in range(chunk_length // 0x200):
            output.write(pack('<L', line))
            output.write('\xff\x00')
            output.write('\xff' * 10)
            line += 1
        for i in range(0x7c - (chunk_length / 0x200)):
            output.write('\xff' * 32)
        output.write('\xff' * 32)
        output.write('\xff\xff\x00\xff')
        output.write('\xff' * 12)
        output.write('\xf0\xf0\x03\x00\x00\x00\xf0\xf0')
        output.write('\xff' * 8)
        d = stream.read(0xf800)
    output.seek(0, 0)
    return output

class FAT16(ObjectWithStream):
    def __init__(self, data, hasPadding=False, isVerbose=True):
        self.hasPadding = hasPadding
        self.isVerbose = isVerbose
        if len(data) < 0x100:
            self.stream  = file(data, 'rb')
        else:
            self.stream = StringIO()
            self.stream.write(data)
        stream = self.stream
        stream.seek(0, 0)
        if hasPadding:
            data = stream.read()
            self.stream1, self.stream2 = splitXGoldStream(data)
            stream = self.stream1
            self.stream = stream
            stream.seek(0, 0)
        self.clustersToFilesDic = {}
        self.parseHeaders()
        if (self.bytesPerSector - stream.tell()) > 0:
            self.bootSecPadding = stream.read(self.bytesPerSector - stream.tell())
        else:
            self.bootSecPadding = ''
        self.bytesPerCluster = self.bytesPerSector * self.sectorsPerCluster
        #self.reservedSectors = stream.read(self.reserverSectorsCount * self.bytesPerSector)
        # Parse the FAT
        self.printIfVerbos("Data starts at 0x%x" % stream.tell())
        if 2 != self.numOfTables:
            self.printIfVerbos("More than two tables stop parsing")
            return
        self.tables = []
        for i in range(self.numOfTables):
            self.printIfVerbos("Table %d starts at 0x%x" % (i, stream.tell()))
            tableData = stream.read(self.sectorsPerFAT * self.bytesPerSector)
            table = unpack('<' + ('H' * (len(tableData) / 2)), tableData)
            table = list(table)
            if 0 != (stream.tell() % self.bytesPerSector):
                print("! VTable padding error")
            self.tables.append(table)
        if self.tables[0] != self.tables[1]:
            #raise Exception("! The two FATs do not match")
            print("! The two FATs do not match, using the first one")
        self.table = self.tables[0]
        # Parse root dir
        self.printIfVerbos("Root dir starts at 0x%x" % stream.tell())
        self._rootDirStart = stream.tell()
        self._rootDirSize  = self.maxRootEntries * 0x20
        self._rootDirData = stream.read(self._rootDirSize)
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
        if 0 != (stream.tell() % self.bytesPerSector):
            self.rootDirPadding = stream.read(abs(stream.tell() % (-self.bytesPerSector)))
        else:
            self.rootDirPadding = ''
        self.dataStart = stream.tell()
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
        self.stream.seek(clusterOffset, 0)
        self.stream.write(data)

    def _writeRoot(self, data):
        if len(data) > self._rootDirSize:
            raise Exception("No room for data in root dir")
        elif len(data) < self._rootDirSize:
            data += '\x00' * (self.bytesPerCluster - len(data))
        self.stream.seek(self._rootDirStart, 0)
        self.stream.write(data)
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
        return name.decode('cp1255').encode('utf-16')[2:]

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

    def make(self):
        output = StringIO()
        header = ''
        header += self.jumpOpcode
        header += self.nopOpcode
        header += self.oemName
        header += self.makeWord(self.bytesPerSector)
        header += self.makeByte(self.sectorsPerCluster)
        header += self.makeWord(self.reserverSectorsCount)
        header += self.makeByte(self.numOfTables)
        header += self.makeWord(self.maxRootEntries)
        totalSectors = self.totalSectors
        if totalSectors < 0x10000:
            header += self.makeWord(totalSectors)
        else:
            header += self.makeWord(0)
        header += self.makeByte(self.mediaDescriptor)
        header += self.makeWord(self.sectorsPerFAT)
        header += self.makeWord(self.sectorsPerTrack)
        header += self.makeWord(self.numOfHeads)
        header += self.makeDword(self.hiddenSectors)
        if totalSectors >= 0x10000:
            header += self.makeDword(totalSectors)
        else:
            header += self.makeDword(totalSectors + self.hiddenSectors)
        # Extended BIOS parameter block
        header += self.makeByte(self.physicalDriveNum)
        header += self.makeByte(self.reserved)
        header += self.makeByte(self.extendedBootSig)
        header += self.makeDword(self.diskId)
        header += self.volumeLabel
        header += self.fatType
        header += self.bootCode
        header += self.makeWord(self.bootSectorSig)
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

        self.stream.seek(self.dataStart)
        output.write(self.stream.read())

        output.seek(0, 0)
        if self.hasPadding:
            output = makePaddedImage(output.read())
        return output.read()

    def readPadding(self, paddingLength):
        if 0 != paddingLength:
            paddingZero = self.stream.read(paddingLength)
            if paddingZero.count('\x00') != paddingLength:
                raise Exception("Padded image error")

    def readModPadding(self, paddingMod=0x200):
        paddingLength = abs(self.stream.tell() % (-paddingMod))
        if 0 != paddingLength:
            paddingZero = self.stream.read(paddingLength)
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
            firstCluster = f.firstCluster

    def _getClusterOffset(self, x):
        return self.dataStart + ((x - 2) * self.bytesPerCluster)
                
    def _readCluster(self, x):
        clusterOffset = self._getClusterOffset(x)
        self.stream.seek(clusterOffset, 0)
        return self.stream.read(self.bytesPerCluster)

    def _resolveParents(self, dirObj):
        if not dirObj.isDir():
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
            stream = StringIO(dirData)
        else:
            stream = dirData
        lastNameIndex = 0
        longName = ''
        result = []
        while True:
            entryType = stream.read(13)
            if 0 == len(entryType):
                break
            stream.seek(-13, 1)
            if '\x0f\x00' != entryType[-2:] and '\x00\x00' != entryType[-2:]: 
                #self.printIfVerbos("File at 0x%x" % stream.tell())
                if '' != longName:
                    endPos = longName.find('\xff\xff')
                    if -1 != endPos:
                        longName = longName[:endPos]
                    longName = longName.replace('\x00\x00', '')
                dirEntry = DirEntry(stream, longName)
                if dirEntry.name[0] in ['\x00', '\xff', ' ']:
                    self.printIfVerbos( "File %s is deleted" % dirEntry.name[1:] )
                    pass
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
            elif '\x0f\x00' == entryType[-2:]:
                # Long file name
                lfn = LongFileNameEntry(stream)
                index = lfn.partIndex - 0x40
                if index > lastNameIndex:
                    if '' != longName:
                        self.printIfVerbos("! Long name not used %s (%x, %x)" % (longName, index, lastNameIndex))
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
                file(outputPath + path + f.getName(), 'wb').write(f.rawData)

    def printIfVerbos(self, text):
        if self.isVerbose:
            print text

    def parseHeaders(self):
        stream = self.stream
        self.jumpOpcode      = stream.read(2)           #   0
        self.nopOpcode       = stream.read(1)           #   2
        self.oemName         = stream.read(8)           #   3
        self.bytesPerSector  = self.readWord()         #  11
        self.sectorsPerCluster = self.readByte()       #  13
        self.reserverSectorsCount = self.readWord()    #  14
        self.numOfTables     = self.readByte()         #  16
        self.maxRootEntries  = self.readWord()         #  17
        self.totalSectors    = self.readWord()         #  19
        self.mediaDescriptor = self.readByte()         #  21
        self.sectorsPerFAT   = self.readWord()         #  22
        self.sectorsPerTrack = self.readWord()         #  24
        self.numOfHeads      = self.readWord()         #  26
        self.hiddenSectors   = self.readDword()        #  28
        if 0 == self.totalSectors:
            self.totalSectors    = self.readDword()        #  32
        else:
            self.extendedTotalSecotrs = self.readDword()
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
        self.physicalDriveNum    = self.readByte()     #  36
        self.reserved            = self.readByte()     #  37
        self.extendedBootSig     = self.readByte()     #  38
        self.diskId              = self.readDword()    #  39
        self.volumeLabel         = stream.read(11)      #  43
        self.fatType             = stream.read(8)       #  54
        self.bootCode            = stream.read(448)     #  62
        self.bootSectorSig       = self.readWord()
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
