
#
# In PBL at offset 0x520 is the RSA block
# The RSA is made of d and mondgomri
# The d is read from end to start
# The sig block of the SBL is found at offset 0x100
# SHA1 is done from offset 0x400 to the end
#

from ..general.utile import DATA
from ..general.fat16 import *
from ..general.objectWithStream import *
from ..crypt.rsa import *
import os
from struct import pack, unpack
from cStringIO import StringIO

class ASHA(ObjectWithStream):
    HEADER_MAGIC = '\x91\x64\x1d\xed'
    UNKNOWN_HEADER_PART1 = '0000002E00000002C00000000000000036000000000000002F00000000C00000000000000065'.decode('hex')
    UNKNOWN_HEADER_PART2 = '00000000010100000000000100000000000000'.decode('hex')
    UNKNOWN_HEADER_PART3 = '319750400000000000000000000000000000000000000000'.decode('hex')

    def __init__(self, data):
        if len(data) < 0x100:
            data = file(data, 'rb').read()
        self.data = data
        self.stream = StringIO(data)
        self.blobs = self.unpack()
        self.rsa = RSA()

    def unpack(self):
        magic = self.read(4)
        if magic != self.HEADER_MAGIC:
            raise Exception('Magic marker not found!')

        self.unknownHeaderPart1 = self.read(0x26)
        mainTag = self.read(4)
        if mainTag != '\x00' * 4:
            raise Exception('Parsing error, probebly not ASHA')
        totalLength = self.readDword()
        self.unknownHeaderPart2 = self.read(0x13)
        self.read(1)
        self.version = self.readWord()
        self.readWord()
        if self.version != self.readWord():
            raise Exception("Two different versions in header")
        self.read(1)
        self.unknownHeaderPart3 = self.read(0x18)
        result = []
        while pos < len(data):
            t = self.readDword()
            l = self.readDword()
            blob = self.read(l-8)
            result.append((t,blob))
        return result

    def dumpBlobsToFiles(self, targetPath):
        output_dir = target
        if output_dir[-1] not in ['/', '\\']:
            output_dir += os.sep
        blobs = parseXGoldPack(data)
        if not os.path.isdir(output_dir):
            os.mkdir(output_dir)
        for i, (t, d) in enumerate(self.blobs):
            file(output_dir + '%04x_%x.bin' % (i, t), 'wb').write(d)
        return output_dir

    def findOneOf(self, data, oldPos, dataToSearch):
        pos = len(data)
        for x in dataToSearch:
            newPos = data.find(x, oldPos)
            if x != -1 and newPos < pos:
                pos = newPos
        if len(data) == pos:
            return -1
        return pos

    def getPublicKeys(self):
        headers = [
                '\x00\x04\x00\x00\x03\x00\x00\x00', \
                '\x00\x04\x00\x00\x01\x00\x01\x00' ]
        keys = []
        for t, blob in self.blobs:
            pos = self.findOneOf(blob, 0, headers)
            while -1 != pos:
                key = blob[pos+0x8:pos+0x88]
                key = key[::-1]
                key = int(key.encode('hex'), 16)
                isKey = True
                for prime in [2, 3, 5, 7, 11, 13, 17]:
                    if 0 == (key % prime):
                        # Too easy to break, very unlikly
                        isKey = False
                        break
                if isKey:
                    keys.append(key)
                pos = self.findOneOf(blob, pos + 1, headers)
        return keys

    def decryptSigSBL(self, sig_offset=0x100):
        for t, blob in self.blobs:
            if 'Quantum_Bootloader' in blob:
                sbl = blob
                break
        else:
            raise Exception("Failed to find SBL in blobs")

        keys = self.getPublicKeys()
        print 'SBL of size %x loaded' % len(sbl)
        startPos = sbl.find('Quantum_Bootloader')
        endPos   = sbl.find('\x00', startPos)
        print sbl[startPos:endPos]
        sig = sbl[sig_offset:sig_offset+0x80]
        plain = self.rsa.decryptRsaBlock(sig, key)
        if None == plain:
            raise Exception("Failed to decrypt block")
        print 'Load address: %x' % unpack('<L', plain[-0x1c:-0x18])[0]
        print 'Length: %x' % unpack('<L', plain[-0x18:-0x14])[0]
        print 'Un-signed bytes length: %x' % (len(sbl) - unpack('<L', plain[-0x18:-0x14])[0])
        return plain

    def pack(self, version):
        result = ''
        totalLength = 0
        for blobType, blobData in blobs:
            totalLength += 8
            totalLength += len(blobData)
        result += self.HEADER_MAGIC
        result += self.UNKNOWN_HEADER_PART1
        result += '\x00' * 4 # Main tag type
        result += pack('>L', totalLength)
        result += self.UNKNOWN_HEADER_PART2
        result += '\x00'
        result += pack('>H', version)
        result += '\x00'
        result += '\x00'
        result += pack('>H', version)
        result += '\x00'
        result += self.UNKNOWN_HEADER_PART3
        for blobType, blobData in blobs:
            result += pack('<L', blobType)
            result += pack('<L', len(blobData)+8)
            result += blobData
        return result

    def getFirstBlobOfTypeC(self):
        typeC = None
        for t, blob in self.blobs:
            if 0xc == t:
                typeC = blob
                break
        return typeC

    def updateFirstBlobOfTypeC(self, newBlob):
        typeC = None
        for i, (t, blob) in enumerate(self.blobs):
            if 0xc == t:
                typeC = blob
                break
        if None == typeC:
            raise Exception("Can't find type C blob to update")
        self.blobs[i] = (t, newBlob)

    def fat16FromImage(self, isNewImageFormat=True):
        typeC = self.getFirstBlobOfTypeC()
        if None == typeC:
            raise Exception("Can't find type C blob in Image")
        ebfePos = typeC.find('\xeb\xfe')
        if -1 == ebfePos or ebfePos > 0x100:
            raise Exception("Can't find FAT16 start")
        fat16Data = typeC[ebfePos:]
        self.fat16BlobHeader = typeC[:ebfePos]
        self.fat16 = FAT16(fat16Data, isNewImageFormat=isNewImageFormat, isVerbose=False)
        return self.fat16

    def updateFat16(self, fat16):
        typeC = self.fat16BlobHeader + fat16.make()
        updateFirstBlobOfTypeC(typeC)

    def dumpFat16ImageToDisk(self, outputPath, isNewImageFormat=True):
        fat16 = self.fat16FromImage(isNewImageFormat=isNewImageFormat)
        if not os.path.isdir(outputPath):
            os.mkdir(outputPath)
        fat16.dumpTree(outputPath)
    
