
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

    def updateBlobs(self, blobs, address, plain):
        if len(blobs) < 3:
            # I probebly don't know how to update this
            return blobs
        # Get normal length for blob
        blobType, blobData = blobs[-2]
        if blobType not in [0x14, 0x54]:
            # I don't want to get the normal length of blob from this blob
            return blobs
        normalLength = blobData[1]
        endAddress = address + len(plain)
        blobType, blobData = blobs[-1]
        blobData = list(blobData)
        currentEnd = blobData[0] + blobData[1]
        if endAddress < currentEnd:
            needToRemove = currentEnd - endAddress
            while needToRemove > 0:
                blobType, blobData = blobs[-1]
                blobData = list(blobData)
                blobLen = blobData[1]
                if needToRemove > blobLen:
                    needToRemove -= blobLen
                    blobs = blobs[:-1]
                else:
                    blobData[1] = blobData[0] + needToRemove
                    blobs[-1] = (blobType, blobData)
                    needToRemove = 0
        elif endAddress > currentEnd:
            needToAdd = endAddress - currentEnd
            while needToAdd > 0:
                blobType, blobData = blobs[-1]
                blobData = list(blobData)
                blobLen = blobData[1]
                if blobLen < normalLength:
                    canAddToBlob = normalLength - blobLen
                    if canAddToBlob > needToAdd:
                        blobLen     += needToAdd
                        needToAdd    = 0
                        blobData[1]  = blobLen
                        blobs[-1]    = (blobType, tuple(blobData))
                    else:
                        blobLen     += canAddToBlob
                        needToAdd   -= canAddToBlob
                        blobData[1]  = blobLen
                        blobs[-1]    = (blobType, tuple(blobData))
                elif blobLen == normalLength:
                    newBlobData = blobData[:]
                    newBlobData[0] = blobData[0] + blobData[1]
                    newBlobData[1] = min(normalLength, needToAdd)
                    needToAdd -= newBlobData[1]
                    blobs.append((blobType, tuple(newBlobData)))
                else:
                    raise Exception("Not expecting blob of that size")
        return blobs

    def writeBlobs( self, outputStream, blobs, address, plain ):
        blobs = self.updateBlobs(blobs, address, plain)
        for blobType, blobData in blobs:
            outputStream.writeUInt8(blobType)
            if blobType in [0x14, 0x54, 0x5d]:
                blobAddr    = blobData[0]
                blobLen     = blobData[1]
                endAddress  = blobAddr + blobLen
                plainChunk = plain[blobAddr - address:endAddress - address]
                cipher = self.packData(blobAddr, plainChunk)
                if 0x14 == blobType:
                    outputStream.write(self.createDataBlobType14(
                        cipher, blobAddr).getRawData())
                elif 0x54 == blobType:
                    outputStream.write(self.createDataBlobType54(
                        cipher, blobAddr, blobData[3], blobData[4], blobData[5], blobData[6]).getRawData())
                elif 0x5d == blobType:
                    outputStream.write(self.createDataBlobType5d(
                        cipher, blobAddr, blobData[3], blobData[4], blobData[5], blobData[6], blobData[7], blobData[8]).getRawData())
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
        result.write(extraBytes)
        result.writeUInt32(len(data))
        result.writeUInt32(address)
        headerSum = self.generateBytesSum8Bit(result.getRawData())
        result.writeUInt8(headerSum)
        result.write(data)
        result.seek(0)
        return result

    def createDataBlobType5d(self, data, address, subType, someFlags, sha1Digest, name, anotherSha1, extraBytes): 
        data = self.validateCreateDataBlobInput(data)
        result = self.ObjectWithStream()
        result.writeUInt16(subType)
        headerLength = 0x2d
        if anotherSha1:
            headerLength += 0x14
        headerLength += len(extraBytes)
        result.writeUInt8(headerLength)
        result.write(sha1Digest)
        result.write(name + ('\x00' * (0xc - len(name))))
        for flag in someFlags:
            result.writeUInt8(flag)
        dataCheck = self.generateDataCheck16Bit(data)
        result.writeUInt16(dataCheck)
        result.writeUInt32(len(data))
        result.writeUInt32(address)
        if anotherSha1:
            result.write(anotherSha1)
        result.write(extraBytes)
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
                address, blobLen, data = (blob[0], blob[1], blob[2])
                endAddress = address + blobLen
                if None == base:
                    base = address
                offset = address - base
                if result.tell() > offset:
                    print "Overlapped blobs! (%x to %x) - Patching data" % (address, endAddress)
                    result.seek(offset)
                elif result.tell() < offset:
                    result.write('\xff' * (offset - result.tell()))
                result.write(data.getRawData())
                result.seek(0, 2)
        return (base, result)

    def extractPlain( self, blobs ):
        data = self.extractData(blobs)
        return (data[0], data[1].getRawData())

    def packData(self, address, plain):
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

