
import cStringIO
from struct import pack, unpack

class ObjectWithStream(object):
    def __init__(self, data=None):
        if None != data:
            self.stream = cStringIO.StringIO(data)
            self.stream.seek(0)
        else:
            self.stream = cStringIO.StringIO()
        self.offsetsHistory = []
    def read(self, length=None):
        if None == length:
            return self.stream.read()
        return self.stream.read(length)
    def readFromTo(self, start, end):
        self.seek(start, 0)
        return self.read(end-start)
    def pushOffset(self):
        self.offsetsHistory.append(self.tell())
    def popOffset(self):
        self.seek(self.offsetsHistory.pop())
    def write(self, data):
        self.stream.write(data)
    def seek(self, offset, whence=0):
        self.stream.seek(offset, whence)
    def tell(self):
        return self.stream.tell()
    def readUInt32(self):
        return unpack('<L', self.stream.read(4))[0]
    def readUInt16(self):
        return unpack('<H', self.stream.read(2))[0]
    def readUInt8(self):
        return ord(self.stream.read(1))
    def makeUInt32(self, x):
        return pack('<L', x)
    def makeUInt16(self, x):
        return pack('<H', x)
    def makeUInt8(self, x):
        return chr(x)
    def writeUInt32(self, x):
        self.stream.write(pack('<L', x))
    def writeUInt16(self, x):
        self.stream.write(pack('<H', x))
    def writeUInt8(self, x):
        self.stream.write(chr(x))
    def readMBInt(self):
        continueBit = True
        result = 0
        while continueBit:
            result <<= 7
            nextByte = self.readByte()
            result += (nextByte & 0x7f)
            continueBit = nextByte & 0x80
        return result
    def writeMBInt(self, x):
        result = chr(x & 0x7f)
        x >>= 7
        while x > 0:
            result = chr((x & 0x7f) | 0x80) + result
            x >>= 7
        self.stream.write(result)
    def writeData(self, data):
        self.stream.write(data)
    def alignPos(self, aligment=4):
        if 0 != self.stream.tell():
            self.stream.read(aligment - (self.stream.tell() % aligment))
    def readString(self, isUTF16=False):
        result = ''
        if isUTF16:
            nextByte = self.stream.read(2)
        else:
            nextByte = self.stream.read(1)
        while nextByte not in ['\x00', '\x00\x00']:
            result += nextByte
            if isUTF16:
                nextByte = self.stream.read(2)
            else:
                nextByte = self.stream.read(1)
        return result
    def getRawData(self):
        currentPos = self.tell()
        self.seek(0,0)
        rawData = self.read()
        self.seek(currentPos, 0)
        return rawData

    def peek(self, length):
        currentPos = self.tell()
        result = self.read(length)
        self.seek(currentPos, 0)
        return result

    def peekOnRestOfData(self):
        currentPos = self.tell()
        rawData = self.read()
        self.seek(currentPos, 0)
        return rawData

    def __len__(self):
        currentPos = self.tell()
        self.seek(0, 2)
        result = self.tell()
        self.seek(currentPos, 0)
        return result

class ObjectWithStreamBigEndian(ObjectWithStream):
    def readUInt32(self):
        return unpack('>L', self.stream.read(4))[0]
    def readUInt16(self):
        return unpack('>H', self.stream.read(2))[0]
    def makeUInt32(self, x):
        return pack('>L', x)
    def makeUInt16(self, x):
        return pack('>H', x)
    def writeUInt32(self, x):
        self.stream.write(pack('>L', x))
    def writeUInt16(self, x):
        self.stream.write(pack('>H', x))
    def readString(self, isUTF16=False):
        result = ''
        if isUTF16:
            nextByte = self.stream.read(2)[::-1]
        else:
            nextByte = self.stream.read(1)
        while nextByte not in ['\x00', '\x00\x00']:
            result += nextByte
            if isUTF16:
                nextByte = self.stream.read(2)[::-1]
            else:
                nextByte = self.stream.read(1)
        return result

