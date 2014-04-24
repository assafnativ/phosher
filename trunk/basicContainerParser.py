
from .interfaces import ContainerParser

from .general.objectWithStream import *
from .general.util import *

class BasicContainerParser(ContainerParser):
    def __init__(self, fileStream, isBigEndian, isVerbose=False):
        self.isVerbose = isVerbose
        self.isBigEndian = isBigEndian
        if isBigEndian:
            self.ObjectWithStream = ObjectWithStreamBigEndian
        else:
            self.ObjectWithStream = ObjectWithStream

    def readBlobs(self, stream):
        length = len(stream)
        blobs = []
        while stream.tell() < length:
            pos = stream.tell()
            blobType = stream.readUInt8()
            blobData = self.parseBlob(blobType, stream)
            blobs.append((blobType, blobData))
        return blobs

    def writeBlobs( self, outputStream, blobs, address, plain ):
        for blobType, blobData in blobs:
            outputStream.writeUInt8(blobType)
            if blobType in [0x14, 0x54]:
                blobAddr     = blobData[0]
                endAddress  = blobData[1]
                plainChunk = plain.readFromTo(blobAddr - address, endAddress - address)
                cipher = self.encrypt(blobAddr, plainChunk)
                if 0x14 == blobType:
                    outputStream.write(self.createDataBlobType14(
                        cipher, blobAddr).getRawData())
                elif 0x54 == blobType:
                    outputStream.write(self.createDataBlobType54(
                        cipher, blobAddr, blobData[3], blobData[4], blobData[5], blobData[6]).getRawData())
                else:
                    raise Exception("Don't know how to produce data blob to type %x" % blobType)
            else:
                raise Exception("Don't know how to encode blob of type %x" % blobType)
        outputStream.seek(0)
        return outputStream

    def validateCreateDataBlobInput(self, data):
        if isinstance(data, (ObjectWithStream, ObjectWithStreamBigEndian)):
            data = data.getRawData()
        if 0 == len(data):
            raise Exception("Can't make a chunk of length zero")
        return data

    def generateDataCheck16Bit(self, data):
        if self.isBigEndian:
            unpackType = '>'
        else:
            unpackType = '<'
        ints = unpack(unpackType + ('H' * (len(data) / 2)), data)
        result = 0
        for i in ints:
            result ^= i
        return result

    def generateBytesSum8Bit(self, data):
        bytesSum = sum([ord(x) for x in data])
        bytesSum &= 0xff
        return bytesSum ^ 0xff

    def createDataBlobType14(self, data, addr):
        data = self.validateCreateDataBlobInput(data)
        result = self.ObjectWithStream()
        result.writeUInt32(addr)
        dataCheck = (self.generateBytesSum8Bit(data) + 1) & 0xff
        result.writeUInt8(dataCheck)
        lengthBin = pack('>L', len(data))
        result.write(lengthBin[1:])
        rawHeader = result.getRawData()
        headerSum = sum([ord(x) for x in rawHeader]) & 0xff
        result.writeUInt8(headerSum ^ 0xff)
        result.write(data)
        result.seek(0)
        return result

    def createDataBlobType54(self, data, address, subType, flashId, someFlag, extraBytes):
        data = self.validateCreateDataBlobInput(data)
        result = self.ObjectWithStream()
        result.writeUInt16(subType)
        result.writeUInt8(0xe + len(extraBytes))
        for fId in flashId:
            result.writeUInt8(fId)
        dataCheck = self.generateDataCheck16Bit(data)
        result.writeUInt16(dataCheck)
        result.writeUInt8(someFlag)
        if extraBytes not in ['', None]:
            result.write(extraBytes)
        result.writeUInt32(len(data))
        result.writeUInt32(address)
        headerSum = self.generateBytesSum8Bit(result.getRawData())
        result.writeUInt8(headerSum)
        result.write(data)
        result.seek(0)
        return result

    def extractData( self, blobs ):
        base = None
        result = self.ObjectWithStream()
        for blobType, blob in blobs:
            if blobType in [0x54, 0x14]:
                address, endAddress, data = (blob[0], blob[1], blob[2])
                if None == base:
                    base = address
                offset = address - base
                if result.tell() > offset:
                    raise Exception("Overlapped blobs!")
                elif result.tell() < offset:
                    result.write('\xff' * (offset - result.tell()))
                result.write(data.getRawData())
        return (base, result)

    def extractPlain( self, blobs ):
        return self.extractData(blobs)

    def encrypt(self, address, plain):
        # Default - No encryption
        return plain

    def readTokens(self, stream):
        tokensLength = stream.readUInt32()
        tokensData = self.ObjectWithStream(stream.read(tokensLength))
        printIfVerbose("Loading Tokens blob length %x" % tokensLength, self.isVerbose)
        return self.decodeTokens(tokensData)

    def writeTokens(self, outputStream, tokens, restOfData):
        # Write the tokens
        tokensStream = self.encodeTokens(tokens)
        outputStream.writeUInt32(len(tokensStream))
        outputStream.write(tokensStream.getRawData())

