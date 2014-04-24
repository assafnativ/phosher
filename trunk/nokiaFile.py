
from .interfaces import ParserInterface
from .general.util import *
from .general.objectWithStream import *

from .bb5.parser import BB5
from .dct4.parser import DCT4
from .asha.parser import ASHA

class NokiaFile(ParserInterface):
    def __init__(self, data, isVerbose=False):
        self.isVerbose = isVerbose
        if len(data) < 0x100:
            data = file(data, 'rb').read()
        self.rawData = data
        self.decode()

    def guessEndianity(self):
        if unpack('>L', self.rawData[1:5]) > unpack('<L', self.rawData[1:5]):
            self.isBigEndian = False
        else:
            self.isBigEndian = True

    def setEndiantiyByFileType(self, fileType):
        if fileType in [0xa2, 0xb2]:
            self.guessEndianity()
        elif 0x91 == self.fileType:
            self.isBigEndian = False
        else:
            raise Exception('File type %x not supported' % self.fileType)

    def decode(self):
        self.fileType = ord(self.rawData[0])
        # Set the engianity
        self.setEndiantiyByFileType(self.fileType)
        printIfVerbose( "Decoding file type 0x%s" % self.fileType, self.isVerbose )
        if self.isBigEndian:
            self.ObjectWithStream = ObjectWithStreamBigEndian
        else:
            self.ObjectWithStream = ObjectWithStream
        
        # Make an access to the file data
        self.fileStream = self.ObjectWithStream(self.rawData)
        self.fileStream.seek(1, 0)

        # Set the right parser for this file type
        if 0xA2 == self.fileType:
            self.containerParser = DCT4(self.fileStream, self.isBigEndian, isVerbose=self.isVerbose)
        elif 0xB2 == self.fileType:
            self.containerParser = BB5(self.fileStream, self.isBigEndian, isVerbose=self.isVerbose)
        elif 0x91 == self.fileType:
            self.containerParser = ASHA(self.fileStream, self.isBigEndian, isVerbose=self.isVerbose)
        else:
            raise Exception('File type %x not supported' % self.fileType)

        # Read the tokens
        self.tokens = self.containerParser.readTokens(self.fileStream)

        # Parse blobs
        self.blobs = self.containerParser.readBlobs(self.fileStream)

        self.address, self.extractedData = self.containerParser.extractData(self.blobs)
        self.endAddress = self.address + len(self.extractedData)

        # Parse things that are special for this file type
        plainAddress, self.plain = self.extractPlain()
        if (plainAddress != self.address):
            raise Exception("This scenario is not supported at the moment")

    def encode( self ):
        blobsData = self.ObjectWithStream()
        self.containerParser.writeBlobs(blobsData, self.blobs, self.address, self.plain)
        self.blobsDataLength = len(blobsData)
        tokensData = self.ObjectWithStream()
        self.containerParser.writeTokens(tokensData, self.tokens)
        return chr(self.fileType) + tokensData.getRawData() + blobsData.getRawData()

    def extractData(self):
        return self.containerParser.extractData(self.blobs)

    def extractPlain(self):
        return self.containerParser.extractPlain(self.blobs)
