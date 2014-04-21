
from abc import ABCMeta, abstractmethod

class ParserInterface( object ):
    """ Pure Interface for Parser """
    __metaclass__ = ABCMeta

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

class ContainerParser( object ):
    """ Pure Interface for Parser """
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self):
        """ Pure virtual """
        raise NotImplementedError("Pure function call")

    @abstractmethod
    def readBlobs(self):
        """ Pure virtual """
        raise NotImplementedError("Pure function call")
        
    @abstractmethod
    def writeBlobs(self, outputStream):
        """ Pure virtual """
        raise NotImplementedError("Pure function call")

    @abstractmethod
    def readTokens(self):
        """ Pure virtual """
        raise NotImplementedError("Pure function call")

    @abstractmethod
    def writeTokens(self, outputStream):
        """ Pure virtual """
        raise NotImplementedError("Pure function call")
