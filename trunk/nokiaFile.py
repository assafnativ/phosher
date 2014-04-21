
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
        self.fileStream.seek(1)

        # Set the right parser for this file type
        if 0xA2 == self.fileType:
            self.containerParser = DCT4(self.fileStream, self.isBigEndian, isVerbose=self.isVerbose)
        elif 0xB2 == self.fileType:
            self.containerParser = BB5(self.fileStream, self.isBigEndian)
        elif 0x91 == self.fileType:
            self.containerParser = ASHA(self.fileStream, self.isBigEndian)
        else:
            raise Exception('File type %x not supported' % self.fileType)

        # Read the tokens
        self.tokens = self.containerParser.readTokens()

        # Parse blobs
        self.blobs = self.containerParser.readBlobs()

        self.address, self.extractedData = self.extractData()
        self.endAddress = self.address + len(self.extractedData)

        # Parse things that are special for this file type
        self.plain = self.containerParser.extractPlain()

    def encode( self ):
        blobsData = self.ObjectWithStream()
        self.containerParser.writeBlobs(blobsData)
        self.blobsDataLength = len(blobsData)
        tokensData = self.ObjectWithStream()
        self.containerParser.writeTokens(tokensData)
        return tokensData.getRawData() + blobsData.getRawData()

    def extractData( self ):
        base = None
        result = self.ObjectWithStream()
        for blobType, blob in self.blobs:
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

    def extractPlain( self ):
        return self.ObjectWithStream(self.extractData.getRawData())
