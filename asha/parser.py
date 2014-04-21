
#
# In PBL at offset 0x520 is the RSA block
# The RSA is made of d and mondgomri
# The d is read from end to start
# The sig block of the SBL is found at offset 0x100
# SHA1 is done from offset 0x400 to the end
#

from ..basicContainerParser import BasicContainerParser
from ..general.util import *
from ..general.objectWithStream import *

from struct import pack, unpack

class ASHA(BasicContainerParser):
    def __init__(self, fileStream, isBigEndian, isVerbose=False):
        BasicContainerParser.__init__(self, fileStream, isBigEndian, isVerbose=isVerbose)

    def parseTokens(self, data):
        tokensData = self.ObjectWithStreamBigEndian(data)
        result = {}
        result['check'] = tokensData.readUInt16()
        unknowns = []
        unknowns.append(tokensData.read(0x2a))
        result['dataLength'] = tokensData.readUInt32()
        unknowns.append(tokensData.read(0x12))
        result['version'] = tokensData.readUInt32()
        if result['version'] != tokensData.readUInt32():
            raise Exception("Versions do not much")
        result['name'] = tokensData.readString()
        result['padding'] = tokensData.read()
        result['unknowns'] = unknowns
        return result

    def readTokens(self):
        tokensLength = self.fileStream.readUint8()
        tokensData = self.fileStream.read(tokensLength - 1)
        return self.parseTokens(tokensData)

    def encodeTokens(self):
        result = self.ObjectWithStreamBigEndian()
        result.writeUInt16(self.tokens['check']) # I don't know how to fix that
        result.write(self.tokens['unknowns'][0])
        result.writeUInt32(self.blobsDataLength)
        result.write(self.tokens['unknowns'][1])
        result.writeUInt32(self.tokens['version'])
        result.writeUInt32(self.tokens['version'])
        result.writeString(self.tokens['name'])
        result.write(self.tokens['padding'])
        return result

    def writeTokens(self, outputStream):
        tokensStream = self.encodeTokens()
        outputStream.writeUInt8(len(tokensStream))
        outputStream.write(tokensStream.getRawData())

    def readBlobs(self):
        length = len(self.fileStream)
        blobs = []
        while self.fileStream.tell() < length:
            blobType = self.fileStream.readUint32()
            blobLength = self.fileStream.readUInt32()
            if 0x0c == blobType:
                zeros = self.fileStream.read(0x10)
                if '\x00' * 0x10 != zeros:
                    raise Exception("Blob type 0xc decoding error")
                supposedEvenXor = self.fileStream.readUint8()
                supposedOddXor  = self.fileStream.readUint8()
                twoZeros = self.fileStream.read(2)
                if '\x00\x00' != twoZeros:
                    raise Exception("Blob type 0xc decoding error")
                dataLength = self.fileStream.readUInt32()
                zero = self.fileStream.readUInt32()
                if 0 != zero:
                    raise Exception("Blob type 0xc decoding error")
                somethingImportant = self.fileStream.readUInt32()
                blobData = self.fileStream.read(dataLength)
                evenXor = 0
                oddXor = 0
                for i in xrange(0, len(blobData), 2):
                    evenXor ^= blobData[i]
                    oddXor  ^= blobData[i+1]
                if evenXor != supposedEvenXor or oddXor != supposedOddXor:
                    raise Exception("Worng XOR check in data blob")
                blobs.append((blobType, (blobData, somethingImportant)))
            else:
                blobData = self.fileStream.read(blobLength - 8)
                blobs.append((blobType, blobData, blobFlags))

    def writeBlobs(self, outputStream):
        for blobType, blobData in self.blobs:
            outputStream.writeUInt32(blobType)
            if 0x0c == blobType:
                blobData, somethingImportant = blobData
                outputStream.write('\x00' * 0x10)
                evenXor = 0
                oddXor  = 0
                for i in xrange(0, len(blobData), 2):
                    evenXor ^= blobData[i]
                    oddXor  ^= blobData[i+1]
                outputStream.writeUInt8(evenXor)
                outputStream.writeUInt8(oddXor)
                outputStream.writeUInt16(0)
                outputStream.writeUInt32(len(blobData))
                outputStream.writeUInt32(0)
                outputStream.writeUInt32(somethingImportant)
                outputStream.write(blobData)
            else:
                outputStream.write(blobData)

    def extractData(self):
        # Just return the largest blob of type 0xc.
        # I have not better solution for that at this point
        result = ''
        for blobType, blobData in self.blobs:
            if 0xc == blobType and len(blobData[0]) > len(result):
                result = blobData[0]
        return blobData

    
