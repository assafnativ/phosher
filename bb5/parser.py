
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

    def parseBlob( self, blobType, dataStream ):
        if 0x54 == blobType:
            subType = dataStream.readUInt16()
            headerLength = dataStream.readUInt8()
            flashId = [ord(x) for x in dataStream.read(3)]
            dataCheck = dataStream.readUInt16()
            someFlag = dataStream.readUInt8()
            if 0xe < headerLength:
                extraBytes = dataStream.read(headerLength - 0xe)
            else:
                extraBytes = ''
            blobLength = dataStream.readUInt32()
            address = dataStream.readUInt32()
            headerSum = dataStream.readUInt8()
            blobData = self.ObjectWithStream(dataStream.read(blobLength))
            blobData.seek(0)
            data = self.parseDataBlob(blobData, dataCheck)
            return (address, address + blobLength, data, subType, flashId, someFlag, extraBytes)
        else:
            raise Exception("Don't know how to parse blob of type %x in file type %x" % (blobType, self.fileType))

    def readTokens(self):
        tokensLength = self.fileStream.readUInt32()
        return self.fileStream.read(tokensLength)

    def writeTokens(self, outputStream):
        outputStream.writeUInt32(len(self.tokens))
        outputStream.write(self.tokens)
