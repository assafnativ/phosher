

from ..general.utile import *
from ..general.patcher import DATA
from ..general.objectWithStream import *

from .wordsPermTable import *
from .inversWordsPermTable import *

from cStringIO import StringIO
from struct import unpack, pack
from hashlib import sha1

IS_LITTLE_ENDIAN = 0        # 0 is big endian 1 is little

# These are also constants in the Trix
DEFAULT_TOKENS = [
        (194, 'DCT4\x00'),
        (195, 'DCT4 ALGORITHM\x00'),
        (218, '\x01'),
        (201, '\x08'),
        (202, '\r\x0c'),
        (203, '\xe4\x11 B\x00\x01\x00\x1f\x00\x03\x00\x00\x00\x00\xff\xff\x00\x00\x00\x00#\\\x04\x0f\x00\x00\x03@\xc6\x05"\x90'),
        (205, '\x00\x01\x86\xa0\x00\x00\x00\x00'),
        (206, '\x00c.\xa0\x00\x00\x00\x00'),
        (207, '\x00c.\xa0\x00\x00\x00\x00'),
        (209, '\x00\x00\xc78\x00\x00\x00\x00'),
        (212, '1`1a1b1d1f1h'),
        (200, '\x01\x00\x00\x00\x01\x01\xff\xff\x01\x02\x00\x00\x01\xcd\xff\xff'),
        (211, 'D\x03$w\xf4\x00\x11\xef>W.\xb8;\x16I\x95\xf2\xdb\x1c\xa5\x7f\xa1\xf6\x87\x99\x90\x14\x00\x9e\xfe\xc8\x91\xd88\x1c=o\x1e\xbb\xdbxc\xf8l\x17\rsqP\x05G\xcd\xf7\x16\xf8\x1a\xb2\x8f\xe5%F\x18\x0e\x9b') ]
DEFAULT_TOKENS_FOR_IMAGE = [
        (194, 'DCT4\x00'),
        (195, 'DCT4 ALGORITHM\x00'),
        (218, '\x01'),
        (201, '\x08'),
        (202, '\r\x0c'),
        (203,
         '\xe4\x11 B\x00\x01\x00\x1f\x00\x03\x00\x00\x00\x00\xff\xff\x00\x00\x00\x00#\\\x04\x0f\x00\x00\x03@\xc6\x05"\x90'),
        (205, '\x00\x01\x86\xa0\x00\x00\x00\x00'),
        (206, '\x00c.\xa0\x00\x00\x00\x00'),
        (207, '\x00c.\xa0\x00\x00\x00\x00'),
        (209, '\x00\x00\xc78\x00\x00\x00\x00'),
        (212, '1`1a1b1d1f1h'),
        (230, '\x00\x11'),
        (200, '\x02\x18\x00\x00\x02\xe7\xff\xff\x02\xe8\x00\x00\x02\xfb\xff\xff'),
        (228, '\x00'),
        (211,
         '@_\xbe\xae\x91:2\xb04n\xb0+\xf6\xe5\xffo\x95\r\xe72\xf1\x18\x01\xe5*]\\\xc4\x93\x84*I\xd6\x0e\xe7c\x8e\x13\x1f\xeb\xa36uC\xccf\xff\xbc\xe6\x99S\x14[{\x84\x08&.\xff\xeb\x98\xbe\xb5\xec')]
DEFAULT_TOKENS_FOR_PPM = [
        (194, 'DCT4\x00'),
        (195, 'DCT4 ALGORITHM\x00'),
        (218, '\x01'),
        (201, '\x08'),
        (202, '\r\x0c'),
        (203,
        '\xe4\x11 B\x00\x01\x00\x1f\x00\x03\x00\x00\x00\x00\xff\xff\x00\x00\x00\x00#\\\x04\x0f\x00\x00\x03@\xc6\x05"\x90'),
        (205, '\x00\x01\x86\xa0\x00\x00\x00\x00'),
        (206, '\x00c.\xa0\x00\x00\x00\x00'),
        (207, '\x00c.\xa0\x00\x00\x00\x00'),
        (209, '\x00\x00\xc78\x00\x00\x00\x00'),
        (212, '1`1a1b1d1f1h'),
        (200, '\x01\xce\x00\x00\x02\x17\xff\xff'),
        (217, '\x00\x08'),
        (211,
        '\xad\xdc\xe5\x89\xc2\x94\xe7\x86m\x9c\x11gc\xb8\xbd\xad\x85*\xde,\xfd\xb8{\xfc\x0f\x96\xb0\xd34\x1cs\x13\x80\xee\x88=\x7f\x86h\x19\xe7p-\xe7\xd4\x0c\\qa\xb8\x9c\xc4\x0f\x88\x15h\xb3M\x02\xab<8\x0f\x82')]
        

DEFAULT_SECTIONS = [
        (0, 0x2c, 0x01000000),
        (0x64, None, 0x01000064) ]
DEFAULT_SECTIONS_FOR_IMAGE = [
        (0, None, 0x2180000) ]
DEFAULT_SECTIONS_FOR_PPM = [
        (0, None, 0x1ce0000) ]

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
    

def decodeMcusw( fileName, isVerbose=False, allowTrixChecksumBug=False, isObfuscated=True, codeBase=None ):
    data = file(fileName, 'rb').read()
    tokens, data = decodeDct4(data, isVerbose, allowTrixChecksumBug, codeBase)
    if isObfuscated:
        plain = data[:ENCRYPTION_START_OFFSET]
        printIfVerbose( "Decrypting 0x%x bytes of data" % (len(data) - ENCRYPTION_START_OFFSET), isVerbose )
        plain += decryptSection(data[ENCRYPTION_START_OFFSET:])
    else:
        plain = data
    return (tokens, plain)


def encodeMcusw( outputFileName, plain, tokens=DEFAULT_TOKENS, sections=DEFAULT_SECTIONS, isPlainFileName=False, isVerbose=False, doEncrypt=True ):
    if isPlainFileName:
        plain = file(plain, 'rb').read()
    if doEncrypt:
        printIfVerbose( "Encrypting data from offset 0x%x (The rest is plain)" % ENCRYPTION_START_OFFSET, isVerbose )
        chiper = encryptSection(plain[ENCRYPTION_START_OFFSET:])
        printIfVerbose( "Done encryption!", isVerbose )
        finalData = plain[:ENCRYPTION_START_OFFSET] + chiper
    else:
        finalData = plain
    data = encodeDct4(finalData, tokens, sections, isVerbose)
    file(outputFileName, 'wb').write(data)

# MGES = *(GATS + 0x14)
# GATS = *(MGES + 0x18)
# Next GATS = *(GATS + 0x18)

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


def checkPlainChecksum( plain, isVerbose=True, base=0x1000084 ):
    currentChecksum = unpack('>H', plain[0x26:0x26+2])[0]
    start = unpack('>L', plain[0x78:0x78+4])[0]
    end = unpack('>L', plain[0xfc:0xfc+4])[0] + 1
    checksum = 0
    for pos in xrange(start - base, end - base, 2):
        checksum += (ord(plain[pos]) * 0x100) + ord(plain[pos+1]) # + unpack('>H', plain[pos:pos+2])[0]
        checksum &= 0xffff
    if isVerbose:
        if currentChecksum != checksum:
            print 'Current checksum 0x%04x is not right, correct checksum is 0x%04x' % (currentChecksum, checksum)
        else:
            print 'Checksum ok 0x%04x' % checksum
    return checksum

def fixChecksum( plain, base=0x1000084, doResetCodeEnd=True ):
    end = unpack('>L', plain[0xfc:0xfc+4])[0]
    if doResetCodeEnd and (end != (len(plain) - 1 + base)):
        newEnd = len(plain) - 1 + base
        print '!! Setting new binary end address to 0x%08x' % newEnd
        plain = plain[:0xfc] + pack('>L', newEnd) + plain[0xfc+4:]
    # The checkPlainChecksum function read the binary end address from the plain
    checksum = checkPlainChecksum( plain, isVerbose=False, base=base )
    plain = plain[:0x26] + pack('>H', checksum) + plain[0x26+2:]
    return plain

def fixSHA1( plain, SHA1TableOffset, base=0x1000084, doResetCodeEnd=True ):
    startAddr, endAddr = unpack('>LL', plain[SHA1TableOffset:SHA1TableOffset+8])
    if doResetCodeEnd:
        codeEndAddr = unpack('>L', plain[0xfc:0xfc+4])[0]
        newEndAddr = len(plain) - 1 + base
        if newEndAddr != newEndAddr:
            print '!! Fix SHA1 function setting new binary end address to 0x%08x' % newEndAddr
            plain = plain[:0xfc] + pack('>L', newEndAddr) + plain[0xfc+4:]

    index = 0
    while (0 != startAddr) and (0 != endAddr):
        if doResetCodeEnd:
            if (newEndAddr != codeEndAddr) and (endAddr == codeEndAddr):
                print 'Last SHA1 block current end 0x%x' % endAddr,
                endAddr = newEndAddr
                tableOffset = SHA1TableOffset + (index * 0x1c) + 4
                plain = plain[:tableOffset] + pack('>L', newEndAddr) + plain[tableOffset+4:]
                print 'new end 0x%x' % endAddr
        tableOffset = SHA1TableOffset + (index * 0x1c) + 8
        currentSHA1Digest = plain[tableOffset:tableOffset + 0x14]
        startOffset = startAddr - base
        endOffset = endAddr - base
        digest = sha1(plain[startOffset:endOffset+1]).digest()
        if digest != currentSHA1Digest:
            print 'Fixing SHA1 digest for address 0x%x:0x%x to %s' % (startAddr, endAddr, digest.encode('hex'))
            plain = plain[:tableOffset] + digest + plain[tableOffset + 0x14:]
        else:
            print 'SHA1 digest for address 0x%x:0x%x is ok (%s)' % (startAddr, endAddr, digest.encode('hex'))
        index += 1
        tableOffset = SHA1TableOffset + (index * 0x1c)
        startAddr, endAddr = unpack('>LL', plain[tableOffset:tableOffset+8])
    return plain

def patchByte( plain, offset, newValue, doFixChecksum=True, isVerbose=True ):
    if type(newValue) != type(''):
        newValue = chr(newValue)
    printIfVerbose( 'Patching BYTE at offset 0x%x' % offset, isVerbose )
    printIfVerbose( 'Old value 0x%02x' % ord(plain[offset]), isVerbose )
    plain = plain[:offset] + newValue + plain[offset+1:]
    printIfVerbose( 'New value 0x%02x' % ord(plain[offset]), isVerbose )
    if doFixChecksum:
        printIfVerbose( 'Fixing checksum', isVerbose )
        plain = fixChecksum( plain, doResetCodeEnd=False )
    return plain

def patchDword( plain, offset, newValue, doFixChecksum=True, isVerbose=True ):
    if type(newValue) != type(''):
        newValue = pack('>L', newValue)
    printIfVerbose( 'Patching DWORD at offset 0x%x' % offset, isVerbose )
    printIfVerbose( 'Old value 0x%s' % plain[offset:offset+4].encode('hex'), isVerbose )
    plain = plain[:offset] + newValue + plain[offset+4:]
    printIfVerbose( 'New value 0x%s' % plain[offset:offset+4].encode('hex'), isVerbose )
    if doFixChecksum:
        printIfVerbose( 'Fixing checksum', isVerbose )
        plain = fixChecksum( plain, doResetCodeEnd=False )
    return plain

def patchBufferAndFixChecksum( plain, offset, newValue, isVerbose=True ):
    plain = patchBuffer( plain, offset, newValue, isVerbose )
    printIfVerbose( 'Fixing checksum', isVerbose )
    plain = fixChecksum( plain, doResetCodeEnd=False )
    return plain

def parsePPM( plain, base=None ):
    if type(plain) == list:
        base = plain[0][0]
        plain = mergeChunks(plain, base)
    if None == base:
        raise Exception('Need base address')
    megic = plain[:4]
    if megic != 'PPM\x00':
        raise Exception("This is not a PPM file")
    ppmVersion = plain[4:4+0x3c].replace('\x00', '').replace('\xff', '')
    ppmVariation = plain[0x40:0x40+4].replace('\x00', '').replace('\xff', '')
    pos = 0x44
    sections = {}
    while pos < len(plain):
        sectionCheck, sectionLength = unpack('>LL', plain[pos:pos+8])[0]
        sectionName = plain[pos+8:pos+0xc]
        sectionData = plain[pos+0xc:pos+sectionLength]
        if sectionName not in sections:
            sections[sectionName] = (sectionCheck, sectionData)
        else:
            raise Exception("Two sections with the same name %s" % sectionName)
        pos += sectionLength
    if len(sections['LPCS'][1]) != 0x228:
        raise Exception('Expecting LPCS section of length 0x22c')
    charSet = []
    lpcs = sections['LPCS'][1][0x24:]
    for i in xrange(0x100):
        charSet.append(lpcs[i*2:i*2+2])
    text = sections['TEXT'][1]
    subChunkName = text[:8].replace('\x00', '');    text = text[8:]
    subChunkLen = unpack('>L', text[:4]);           text = text[4:]
    flags = unpack('BBBB', text[:4]);               text = text[4:]
    return sections

CHUNK_HEADER = 'f0f00001ff000000'.decode('hex')
LAST_CHUNK_HEADER = 'f0f00001ffc00000'.decode('hex')
SECTOR_HEADER = 'fff0ffff'.decode('hex')
NO_SECTOR_HEADER = 'ffffffffffffffff'.decode('hex')
SECTOR_LENGTH = 0x200
SECTORS_PER_CHUNK = 0xFC
CHUNK_LENGTH = SECTOR_LENGTH * SECTORS_PER_CHUNK
CHUNK_FOOTER = 'fffffffffffffffffffffffffffffffffffffffffffff0f0'.decode('hex')

def decodeImageFile( plain, isVerbose=False ):
    if len(plain) < 1024:
        # Must be a file name
        printIfVerbose("Loading data from %s" % plain, isVerbose)
        plain = file(plain, 'rb').read()
    if '\xA2' == plain[0]:
        printIfVerbose("Decoding DCT4 level", isVerbose)
        tokens, plain = decodeDct4(plain)
        printIfVerbose("Done decoding DCT4 level", isVerbose)
    fat16 = ''
    pos = 0
    sector_num = 0
    last = False
    while pos < len(plain):
        if last:
            raise Exception('Data continues past last chunk at 0x%x'%pos)
        if plain[pos:].startswith(CHUNK_HEADER):
            pos += len(CHUNK_HEADER)
            last = False
        elif plain[pos:].startswith(LAST_CHUNK_HEADER):
            pos += len(LAST_CHUNK_HEADER)
            last = True
        else:
            raise Exception('Missing chunk header at 0x%x'%pos)
        for i in xrange(SECTORS_PER_CHUNK):
            if plain[pos:].startswith(SECTOR_HEADER):
                pos += len(SECTOR_HEADER)
                if sector_num != unpack('>L', plain[pos:pos+4])[0]:
                    raise Exception('Wrong sector number at 0x%x'%pos)
                sector_num += 1
                pos += 4
                fat16 += plain[pos:pos+SECTOR_LENGTH]
                pos += SECTOR_LENGTH
            elif plain[pos:].startswith(NO_SECTOR_HEADER):
                pos += len(NO_SECTOR_HEADER)
                if plain[pos:pos+SECTOR_LENGTH] != '\xFF'*SECTOR_LENGTH:
                    raise Exception('Bad sector padding at 0x%x'%pos)
                pos += SECTOR_LENGTH
            else:
                raise Exception('Missing sector header at 0x%x'%pos)
        if not plain[pos:].startswith(CHUNK_FOOTER):
            raise Exception('Missing chunk footer at 0x%x'%pos)
        pos += len(CHUNK_FOOTER)
    if not last:
        raise Exception('Data ended before last chunk')
    parseFat16(fat16)
    return (tokens, fat16)

def encodeImageFile( fat16, tokens=DEFAULT_TOKENS_FOR_IMAGE, sections=DEFAULT_SECTIONS_FOR_IMAGE, isVerbose=False ):
    if len(fat16) < 1024:
        # Must be a file name
        fat16 = file(fat16, 'rb').read()
    sector_num = 0
    plain = ''
    for i in xrange(0, len(fat16), CHUNK_LENGTH):
        if i + CHUNK_LENGTH >= len(fat16):
            plain += LAST_CHUNK_HEADER
        else:
            plain += CHUNK_HEADER
        for j in xrange(0, CHUNK_LENGTH, SECTOR_LENGTH):
            toadd = fat16[i:i+CHUNK_LENGTH][j:j+SECTOR_LENGTH]
            if toadd:
                plain += SECTOR_HEADER
                plain += pack('>L', sector_num)
                sector_num += 1
                plain += toadd + '\xFF' * ((-len(toadd)) % SECTOR_LENGTH)
            else:
                plain += '\xFF' * (len(SECTOR_HEADER) + 4 + SECTOR_LENGTH)
        plain += CHUNK_FOOTER
    data = encodeDct4(plain, tokens, sections, isVerbose )
    return data

