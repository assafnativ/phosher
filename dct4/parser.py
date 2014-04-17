

from ..general.utile import *
from ..general.objectWithStream import *

from .wordsPermTable import *
from .inversWordsPermTable import *

from cStringIO import StringIO
from struct import unpack, pack
from hashlib import sha1

class DCT4(ObjectWithStreamBigEndian):
    TABLE = [ \
        (0x000140, 0x1000), (0x000220, 0x52a1), 
        (0x000480, 0x1221), (0x000600, 0xb928),
        (0x000810, 0x5221), (0x000840, 0x1220), 
        (0x000900, 0x2008), (0x001020, 0x1221),
        (0x001080, 0x0908), (0x001100, 0x52a1), 
        (0x002020, 0x0100), (0x002080, 0xfbbd),
        (0x004010, 0xa91a), (0x004040, 0xa908), 
        (0x008008, 0x2908), (0x009000, 0x1000),
        (0x00a000, 0xbd3a), (0x010010, 0xad1a), 
        (0x010040, 0x5221), (0x010400, 0x0908),
        (0x020200, 0x53a5), (0x040040, 0xa91a), 
        (0x044000, 0x1b20), (0x080100, 0xa918),
        (0x800000, 0xb908) ]
    XOR_TABLE = [ \
        0x0fae, 0x3e7f, 0xc99f, 0xd6f7, 0xa71b, 0x14c4, 0x52a5, 0xcbb1, \
        0x4285, 0xefdf, 0xdff7, 0x5080, 0xee9f, 0x0000, 0x8432, 0x5221, \
        0x4084, 0xa91a, 0x56e7, 0xb93a, 0x5b21, 0xa818, 0x0000, 0xefdf ]
    ENCRYPTED_RANGE = (0x1000084, 0x2000000)

    def __init__(self, data, isVerbose=False):
        self.isVerbose = isVerbose
        if len(data) < 0x100:
            data = file(data, 'rb').read()
        self.rawData = data
        ObjectWithStreamBigEndian.__init__(self, data)
        self.WORDS_PERM_TABLE   = WORDS_PERM_TABLE
        self.INVERS_PERM_TABLE  = INVERS_PERM_TABLE
        self.decode()

    def cryptoInternal( self, word, addr ):
        for mask, xorVal in self.TABLE:
            if mask == (mask & (addr)):
                word ^= xorVal
        bit = 1
        for i in xrange(len(self.XOR_TABLE)):
            if addr & (1 << bit):
                word ^= self.XOR_TABLE[i]
            bit = (bit + 1) & 0x1f
        return word

    def decryptChunk( self, data, base=0x1000084 ):
        result  = ObjectWithStreamBigEndian()
        addr = base
        endAddr = base + len(data)
        while addr < endAddr:
            word = data.readUInt16()
            word = self.cryptoInternal(word, addr)
            word = self.WORDS_PERM_TABLE[word]
            result.writeUInt16(word)
            addr += 2
        return result

    def encryptChunk( self, data, base=0x1000084 ):
        result  = ObjectWithStreamBigEndian()
        addr = base
        endAddr = base + len(data)
        while addr < endAddr:
            word = data.readUInt16()
            word ^= 0x8a1b
            word = self.INVERS_PERM_TABLE[word]
            word = self.cryptoInternal( word, addr )
            result.writeUInt16(word)
            addr += 2
        return result

    def xorWordToData( self, data, xorVal ):
        result = ObjectWithStreamBigEndian()
        dataLength = len(data)
        while dataLength > data.tell():
            result.writeUInt16(data.readUInt16() ^ xorVal)
        return result

    def decrypt( self, data, base=0x1000084 ):
        if isinstance(data, str):
            data = ObjectWithStreamBigEndian(data)
        data = self.decryptChunk(data, base)
        data.seek(0)
        xorVal = data.readUInt16() ^ 0xffff
        data.seek(0)
        data = self.xorWordToData(data, xorVal)
        return data

    def encrypt( self, data, base=0x1000084 ):
        if isinstance(data, str):
            data = ObjectWithStreamBigEndian(data)
        return self.encryptChunk(data, base=base) 

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
            raise Exception("Tokens parssing error")
        return tokens

    def parseDataBlob( self, data, dataCheck ):
        # Just checks the bytesSum
        length = len(data)
        chunks = []
        bytesSum = sum([ord(x) for x in data.getRawData()])
        bytesSum &= 0xff
        bytesSum ^= 0xff
        dataCheck -= bytesSum
        if dataCheck < 0:
            dataCheck += 0x100
        if 1 != dataCheck:
            raise Exception("Data check error!")
        data.seek(0)
        return data

    def readBlobs( self ):
        length = len(self)
        blobs = []
        isBlobEncrypted = False
        printIfVerbose("Parsing file of length %x" % length, self.isVerbose)
        while self.tell() < length:
            pos = self.tell()
            blobType = self.readUInt8()
            if 0xA2 == blobType:
                blobLength = self.readUInt32()
                blobData = ObjectWithStreamBigEndian(self.read(blobLength))
                blobData.seek(0)
                printIfVerbose("Loading Tokens blob (%x) of length %x starting at %x" % (blobType, blobLength, pos), self.isVerbose)
                tokens = self.parseTokens(blobData)
                blobs.append((blobType, tokens))
            elif 0x14 == blobType:
                self.pushOffset()
                address = self.readUInt32()
                dataCheck = self.readUInt8()
                blobLength = unpack('>L', '\x00' + self.read(3))[0]
                self.popOffset()
                header = self.read(8)
                headerSum = sum([ord(x) for x in header]) & 0xff
                headerSum ^= 0xff
                headerCheck = self.readUInt8()
                if headerSum != headerCheck:
                    raise Exception("Header checksum mismatch")
                printIfVerbose("Loading DATA blob (%x) of length %x starting at %x" % (blobType, blobLength, pos), self.isVerbose)
                blobData = ObjectWithStreamBigEndian(self.read(blobLength))
                blobData.seek(0)
                data = self.parseDataBlob(blobData, dataCheck)
                blobs.append((blobType, (address, address + blobLength, data)))
                isBlobEncrypted = True
            else:
                raise Exception("Unknown blob type %x" % blobType)
        return blobs

    def decode( self ):
        self.fileType = self.readUInt8()
        if 0xA2 != self.fileType:
            raise Exception('File type not supported')
        printIfVerbose( "Decoding file type 0x%s" % self.fileType, self.isVerbose )
        self.seek(0)
        self.blobs = self.readBlobs()
        self.address, rawData = self.getRaw()
        self.endAddress = self.address + len(rawData)
        if self.address < self.ENCRYPTED_RANGE[1] and self.endAddress > self.ENCRYPTED_RANGE[0]:
            # There is some encrypted data
            encryptedDataStart  = max(self.address,     self.ENCRYPTED_RANGE[0])
            encryptedDataEnd    = min(self.endAddress,  self.ENCRYPTED_RANGE[1])
            encryptedDataOffset     = encryptedDataStart    - self.address
            encryptedDataEndOffset  = encryptedDataEnd      - self.address
            encryptedDataLength     = encryptedDataEnd - encryptedDataStart
            self.plain = ObjectWithStreamBigEndian()
            printIfVerbose("Data chunk from %x to %x Decrypting data from %x to %x" % (
                self.address, 
                self.endAddress,
                encryptedDataStart,
                encryptedDataEnd), self.isVerbose)
            rawData.seek(0)
            if encryptedDataOffset > 0:
                self.plain.write( rawData.read(encryptedDataOffset) )
            decryptedData = self.decrypt(rawData.read(encryptedDataLength), encryptedDataStart)
            if len(decryptedData) != encryptedDataLength:
                raise Exception("Decrypt returned wrong number of bytes")
            self.plain.write( decryptedData.getRawData() )
            if encryptedDataEnd < self.endAddress:
                self.plain.write( rawData.read() )
        else:
            self.plain = rawData

    def getRaw( self ):
        base = None
        result = ObjectWithStreamBigEndian()
        for blobType, blob in self.blobs:
            if 0x14 == blobType:
                address, endAddress, data = blob
                if None == base:
                    base = address
                offset = address - base
                if result.tell() > offset:
                    raise Exception("Overlapped blobs!")
                elif result.tell() < offset:
                    result.write('\xff' * (offset - result.tell()))
                result.write(data.getRawData())
        return (base, result)

    def createDataBlob(self, data, addr):
        if isinstance(data, (ObjectWithStream, ObjectWithStreamBigEndian)):
            data = data.getRawData()
        if 0 == len(data):
            raise Exception("Can't make a chunk of length zero")
        bytesSum = sum([ord(x) for x in data])
        bytesSum &= 0xff
        bytesSum ^= 0xff
        dataCheck = (1 + bytesSum) & 0xff
        result = ObjectWithStreamBigEndian()
        result.writeUInt32(addr)
        result.writeUInt8(dataCheck)
        lengthBin = pack('>L', len(data))
        result.write(lengthBin[1:])
        rawHeader = result.getRawData()
        headerSum = sum([ord(x) for x in rawHeader]) & 0xff
        result.writeUInt8(headerSum ^ 0xff)
        result.write(data)
        result.seek(0)
        return result

    def tokensToStream(self):
        tokens = None
        for blobType, blobData in self.blobs:
            if 0xa2 == blobType:
                tokens = blobData
                break
        if None == tokens:
            raise Exception("Instance doesn't have tokens")
        result = ObjectWithStreamBigEndian()
        result.writeUInt32(len(tokens))
        printIfVerbose( "Writting %d tokens" % len(tokens), self.isVerbose )
        for tokenId, tokenData in tokens:
            printIfVerbose( "Writting token id=0x%x of 0x%x bytes" % (tokenId, len(tokenData)), self.isVerbose )
            result.writeUInt8(tokenId)
            result.writeUInt8(len(tokenData))
            result.write(tokenData)
        result.seek(0)
        return result

    def encode( self ):
        result = ObjectWithStreamBigEndian()
        for blobType, blobData in self.blobs:
            result.writeUInt8(blobType)
            if 0xa2 == blobType:
                # Write the tokens
                tokensStream = self.tokensToStream()
                result.writeUInt32(len(tokensStream))
                result.write(tokensStream.read())
            elif 0x14 == blobType:
                address, endAddress, _ = blobData
                plain = self.plain.readFromTo(address - self.address, endAddress - self.address)
                if address < self.address or address > self.endAddress:
                    raise Exception("Data out of range")
                if 0 == len(plain):
                    raise Exception("No plain data!")
                if address < self.ENCRYPTED_RANGE[1] and endAddress > self.ENCRYPTED_RANGE[0]:
                    encryptedDataStart  = max(address,     self.ENCRYPTED_RANGE[0])
                    encryptedDataEnd    = min(endAddress,  self.ENCRYPTED_RANGE[1])
                    encryptedDataOffset     = encryptedDataStart    - address
                    encryptedDataEndOffset  = encryptedDataEnd      - address
                    encryptedDataLength     = encryptedDataEnd - encryptedDataStart
                    dataToWrite = ObjectWithStreamBigEndian()
                    if encryptedDataOffset > 0:
                        dataToWrite.write(plain[:encryptedDataOffset])
                    dataToWrite.write(self.encrypt(plain[encryptedDataOffset:encryptedDataEndOffset], encryptedDataStart).getRawData())
                    if encryptedDataEnd < endAddress:
                        dataToWrite.write(plain[encryptedDataEndOffset:])
                else:
                    dataToWrite = plain
                result.write(self.createDataBlob(dataToWrite, address).getRawData())
            else:
                raise Exception("Don't know how to encode blob of type %x" % blobType)

        result.seek(0)
        return result
    

# A2 - The format version / type
# 00 00 00 D2 - The length of the section to follow
# 00 00 00 0D - Number of tokens
# C2 - Token type
# 05 - Token length
# n bytes of token data
# ...
# 14 - Section type (0x14 Flash code)
# 01 00 00 00 - Code address
# 01 - Data check (One byte added to all other to make it one mod 0x100)
# 00 00 2C - Data length (Yes just 3 bytes)
# 01 - Header check byte
# Data
# ...

