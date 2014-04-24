
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

import scipy
from struct import pack, unpack

class ASHA(BasicContainerParser):
    def __init__(self, fileStream, isBigEndian, isVerbose=False):
        self.fileType = 0x91
        BasicContainerParser.__init__(self, fileStream, isBigEndian, isVerbose=isVerbose)

    def parseTokens(self, data):
        tokensData = ObjectWithStreamBigEndian(data)
        result = {}
        result['check'] = tokensData.readUInt16()
        unknowns = []
        unknowns.append(tokensData.read(0x2a))
        result['dataLength'] = tokensData.readUInt32()
        unknowns.append(tokensData.read(0x12))
        result['version'] = tokensData.readUInt32()
        if result['version'] != tokensData.readUInt32():
            raise Exception("Versions do not much")
        tokensData.readUInt8()      # Another zero
        result['name'] = tokensData.readString()
        result['padding'] = tokensData.read()
        result['unknowns'] = unknowns
        return result

    def readTokens(self, fileStream):
        tokensLength = fileStream.readUInt8()
        tokensData = fileStream.read(tokensLength - 1)
        return self.parseTokens(tokensData)

    def encodeTokens(self, tokens, dataLength):
        result = ObjectWithStreamBigEndian()
        result.writeUInt16(tokens['check']) # I don't know how to fix that
        result.write(tokens['unknowns'][0])
        result.writeUInt32(dataLength)
        result.write(tokens['unknowns'][1])
        result.writeUInt32(tokens['version'])
        result.writeUInt32(tokens['version'])
        result.writeUInt8(0)
        result.write(tokens['name'] + '\x00')
        result.write(tokens['padding'])
        return result

    def writeTokens(self, outputStream, tokens, restOfData):
        tokensStream = self.encodeTokens(tokens, len(restOfData))
        outputStream.writeUInt8(len(tokensStream) + 1)
        outputStream.write(tokensStream.getRawData())

    def readBlobs(self, stream):
        length = len(stream)
        blobs = []
        while stream.tell() < length:
            blobType = stream.readUInt32()
            blobLength = stream.readUInt32()
            if 0x0c == blobType:
                zeros = stream.read(0x10)
                if '\x00' * 0x10 != zeros:
                    raise Exception("Blob type 0xc decoding error")
                supposedXor = stream.readUInt16()
                twoZeros = stream.read(2)
                if '\x00\x00' != twoZeros:
                    raise Exception("Blob type 0xc decoding error")
                dataLength = stream.readUInt32()
                zero = stream.readUInt32()
                if 0 != zero:
                    raise Exception("Blob type 0xc decoding error")
                somethingImportant = stream.readUInt32()
                blobData = stream.read(dataLength)
                dataArray = scipy.fromstring(blobData, scipy.uint16)
                calcedXor = scipy.bitwise_xor.reduce(dataArray)
                if calcedXor != supposedXor:
                    raise Exception("Worng XOR check in data blob %x != %x" % (calcedXor, supposedXor))
                blobs.append((blobType, (blobData, somethingImportant)))
            else:
                blobData = stream.read(blobLength - 8)
                blobs.append((blobType, blobData))
        return blobs

    def writeBlobs(self, outputStream, blobs, address, plain):
        for blobType, blobData in blobs:
            outputStream.writeUInt32(blobType)
            if 0x0c == blobType:
                codeData, somethingImportant = blobData
                outputStream.writeUInt32(len(codeData) + 0x20 + 8)
                outputStream.write('\x00' * 0x10)
                dataArray = scipy.fromstring(codeData, scipy.uint16)
                calcedXor = scipy.bitwise_xor.reduce(dataArray)
                outputStream.writeUInt16(calcedXor)
                outputStream.writeUInt16(0)
                outputStream.writeUInt32(len(codeData))
                outputStream.writeUInt32(0)
                outputStream.writeUInt32(somethingImportant)
                outputStream.write(codeData)
            else:
                outputStream.writeUInt32(len(blobData) + 8)
                outputStream.write(blobData)

    def extractData(self, blobs):
        # Just return the largest blob of type 0xc.
        # I have not better solution for that at this point
        result = ''
        for blobType, blobData in blobs:
            if 0xc == blobType and len(blobData[0]) > len(result):
                result = blobData[0]
        return (0, self.ObjectWithStream(result))
