
from abc import ABCMeta, abstractmethod

class ParserInterface( object, metaclass=ABCMeta ):
    """ Pure Interface for Parser """

    @abstractmethod
    def __init__(self):
        """ Pure virtual """
        raise NotImplementedError("Pure function call")

    @abstractmethod
    def decode(self):
        """ Pure virtual """
        raise NotImplementedError("Pure function call")

    @abstractmethod
    def encode(self):
        """ Pure virtual """
        raise NotImplementedError("Pure function call")

    @abstractmethod
    def extractData(self):
        """ Pure virtual """
        raise NotImplementedError("Pure function call")

    @abstractmethod
    def extractPlain(self):
        """ Pure virtual """
        raise NotImplementedError("Pure function call")

class ContainerParser( object, metaclass=ABCMeta ):
    """ Pure Interface for Parser """

    @abstractmethod
    def __init__(self, fileStream, isBigEndian, isVerbose):
        """ Pure virtual """
        raise NotImplementedError("Pure function call")

    @abstractmethod
    def readBlobs(self, stream):
        """ Pure virtual """
        raise NotImplementedError("Pure function call")
        
    @abstractmethod
    def writeBlobs( self, outputStream, blobs, address, plain ):
        """ Pure virtual """
        raise NotImplementedError("Pure function call")

    @abstractmethod
    def readTokens(self):
        """ Pure virtual """
        raise NotImplementedError("Pure function call")

    @abstractmethod
    def writeTokens(self, outputStream, tokens, restOfData):
        """ Pure virtual """
        raise NotImplementedError("Pure function call")

    @abstractmethod
    def extractData( self, blobs ):
        """ Pure virtual """
        raise NotImplementedError("Pure function call")

    @abstractmethod
    def extractPlain( self, blobs ):
        """ Pure virtual """
        raise NotImplementedError("Pure function call")

    @abstractmethod
    def packData(self, address, plain):
        """ Pure virtual """
        raise NotImplementedError("Pure function call")

