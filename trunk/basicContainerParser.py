
from .interfaces import ContainerParser

from .general.objectWithStream import *
from .general.util import *

class BasicContainerParser(ContainerParser):
    def __init__(self, fileStream, isBigEndian, isVerbose=False):
        self.isVerbose = isVerbose
        if isBigEndian:
            self.ObjectWithStream = ObjectWithStreamBigEndian
        else:
            self.ObjectWithStream = ObjectWithStream
        self.fileStream = fileStream
    
    def parseTokens(self, data):
        numOfTokens = data.readUInt32()
        printIfVerbose( "Decoding %d tokens (Total size 0x%x)" % (numOfTokens, len(data)), self.isVerbose )
        tokens = []
        length = len(data)
        while data.tell() < length:
            tokenType = data.readUInt8()
            tokenLen = data.readUInt8()
            tokens.append((tokenType, data.read(tokenLen)))
        if len(tokens) != numOfTokens:
            raise Exception("Tokens parssing error (%x -> %x)" % (numOfTokens, len(tokens)))
        return tokens

    def readTokens(self):
        tokensLength = self.fileStream.readUInt32()
        tokensData = self.ObjectWithStream(self.fileStream.read(tokensLength))
        printIfVerbose("Loading Tokens blob length %x" % tokensLength, self.isVerbose)
        return self.parseTokens(tokensData)

    def writeTokens(self, outputStream):
        # Write the tokens
        tokensStream = self.encodeTokens()
        outputStream.writeUInt32(len(tokensStream))
        outputStream.write(tokensStream.getRawData())

    def readBlobs(self):
        length = len(self.fileStream)
        blobs = []
        while self.fileStream.tell() < length:
            pos = self.fileStream.tell()
            blobType = self.fileStream.readUInt8()
            blobData = self.parseBlob(blobType)
            if 0x54 == blobType:
                if 0xb2 != self.fileType:
                    raise Exception("Invalid blob type %x in non BB5 file" % blobType)
                subType = self.fileStream.readUInt16()
                headerLength = self.fileStream.readUInt8()
                flashId = [ord(x) for x in self.fileStream.read(3)]
                dataCheck = self.fileStream.readUInt16()
                someFlag = self.fileStream.readUInt8()
                if 0xe < headerLength:
                    extraBytes = self.fileStream.read(headerLength - 0xe)
                else:
                    extraBytes = ''
                blobLength = self.fileStream.readUInt32()
                address = self.fileStream.readUInt32()
                headerSum = self.fileStream.readUInt8()
                blobData = self.ObjectWithStream(self.fileStream.read(blobLength))
                blobData.seek(0)
                data = self.parseDataBlob(blobData, dataCheck)
                blobs.append((blobType, (address, address + blobLength, data, subType, flashId, someFlag, extraBytes)))
            elif 0x14 == blobType:
                if 0x14 != self.fileType:
                    raise Exception("Invalid blob type %x in non BB5 file" % blobType)
                self.pushOffset()
                address = self.fileStream.readUInt32()
                dataCheck = self.fileStream.readUInt8()
                blobLength = unpack('>L', '\x00' + self.fileStream.read(3))[0]
                self.popOffset()
                header = self.fileStream.read(8)
                headerSum = sum([ord(x) for x in header]) & 0xff
                headerSum ^= 0xff
                headerCheck = self.fileStream.readUInt8()
                if headerSum != headerCheck:
                    raise Exception("Header checksum mismatch")
                printIfVerbose("Loading DATA blob (%x) of length %x starting at %x" % (blobType, blobLength, pos), self.isVerbose)
                blobData = self.ObjectWithStream(self.fileStream.read(blobLength))
                blobData.seek(0)
                data = self.parseDataBlob(blobData, dataCheck)
                blobs.append((blobType, (address, address + blobLength, data)))
                isBlobEncrypted = True
            else:
                raise Exception("Unknown blob type %x" % blobType)
        return blobs

    def writeBlobs( self, outputStream ):
        for blobType, blobData in self.blobs:
            outputStream.writeUInt8(blobType)
            if blobType in [0x14, 0x54]:
                address     = blobData[0]
                endAddress  = blobData[1]
                plain = self.plain.readFromTo(address - self.address, endAddress - self.address)
                cipher = self.containerParser.produceCipher(address, plain)
                if 0x14 == blobType:
                    outputStream.write(self.createDataBlobType14(cipher, address).getRawData())
                elif 0x54 == blobType:
                    outputStream.write(self.createDataBlobType54(cipher, address, blobData[3], blobData[4], blobData[5], blobData[6]).getRawData())
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
            reuslt ^= i
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

    def createDataBlobType54(self, data, addr, subType, flashId, someFlag, extraBytes):
        data = self.validateCreateDataBlobInput(data)
        result = self.ObjectWithStream()
        result.writeUInt16(subType)
        result.writeUInt8(0xe + len(extraBytes))
        for fId in flashId:
            reuslt.writeUInt8(fId)
        dataCheck = self.generateDataCheck16Bit(data)
        result.writeUInt16(dataCheck)
        result.writeUInt8(someFlag)
        if extraBytes not in ['', None]:
            result.write(extraBytes)
        result.writeUInt32(len(data))
        result.writeUInt32(address)
        headerSum = self.generateBytesSum8Bit(result.getRawData())
        result.writeUInt8(headerSum)
        result.seek(0)
        return result

    def encodeTokens(self):
        tokens = None
        for blobType, blobData in self.blobs:
            if blobType in [0xa2, 0xb2]:
                tokens = blobData
                break
        if None == tokens:
            raise Exception("Instance doesn't have tokens")
        result = self.ObjectWithStream()
        result.writeUInt32(len(tokens))
        printIfVerbose( "Writting %d tokens" % len(tokens), self.isVerbose )
        for tokenId, tokenData in tokens:
            printIfVerbose( "Writting token id=0x%x of 0x%x bytes" % (tokenId, len(tokenData)), self.isVerbose )
            result.writeUInt8(tokenId)
            result.writeUInt8(len(tokenData))
            result.write(tokenData)
        result.seek(0)
        return result

