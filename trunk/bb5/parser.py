
from ..basicContainerParser import BasicContainerParser

class BB5(BasicContainerParser):
    def __init__(self, fileStream, isBigEndian, isVerbose=False):
        self.fileType = 0xb2
        BasicContainerParser.__init__(self, fileStream, isBigEndian, isVerbose=isVerbose)

    def parseDataBlob( self, data, dataCheck ):
        # Just checks the bytesSum
        length = len(data)
        calcDataCheck = self.generateDataCheck16Bit(data.getRawData())
        if dataCheck != calcDataCheck:
            raise Exception("Data check error! (%x)" % dataCheck)
        data.seek(0)
        return data

    def validateHeader(self, data, length):
        header = data.read(length)
        calcHeaderSum = self.generateBytesSum8Bit(header)
        headerSum = data.readUInt8()
        if calcHeaderSum != headerSum:
            raise Exception("Header check sum failed (%x != %x)" % (calcHeaderSum, headerSum))

    def parseBlob( self, blobType, dataStream ):
        if blobType in [0x54, 0x5d]:
            dataStream.pushOffset()
            subType = dataStream.readUInt16()
            headerLength = dataStream.readUInt8()
            if 0x54 == blobType:
                flashId = [ord(x) for x in dataStream.read(3)]
                dataCheck   = dataStream.readUInt16()
                someFlag    = dataStream.readUInt8()
                if 0xe < headerLength:
                    extraBytes = dataStream.read(headerLength - 0xe)
                else:
                    extraBytes = ''
                blobLength  = dataStream.readUInt32()
                address     = dataStream.readUInt32()
                dataStream.popOffset()
                self.validateHeader(dataStream, headerLength + 3)
                blobData = self.ObjectWithStream(dataStream.read(blobLength))
                blobData.seek(0)
                data = self.parseDataBlob(blobData, dataCheck)
                return (address, blobLength, data, subType, flashId, someFlag, extraBytes)
            elif 0x5d == blobType:
                sha1Digest  = dataStream.read(0x14)
                name        = dataStream.read(0xc).replace('\x00', '')
                someFlags   = [ord(x) for x in dataStream.read(3)]
                dataCheck   = dataStream.readUInt16()
                blobLength  = dataStream.readUInt32()
                address     = dataStream.readUInt32()
                if headerLength > 0x2d:
                    anotherSha1 = dataStream.read(0x14)
                    extraBytes = dataStream.read(headerLength - 0x2d - 0x14)
                else:
                    anotherSha1 = None
                    extraBytes = ''
                dataStream.popOffset()
                self.validateHeader(dataStream, headerLength + 3)
                blobData = self.ObjectWithStream(dataStream.read(blobLength))
                blobData.seek(0)
                data = self.parseDataBlob(blobData, dataCheck)
                return (address, blobLength, data, subType, someFlags, sha1Digest, name, anotherSha1, extraBytes)
            else:
                raise Exception("WTF")
        else:
            raise Exception("Don't know how to parse blob of type %x in file type %x (@%x)" % (blobType, self.fileType, dataStream.tell()))

    def decodeTokens(self, data):
        # Don't know how to decode BB5 tokens
        return data

    def encodeTokens(selfs, tokens):
        return tokens


