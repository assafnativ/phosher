
from io import BytesIO
from struct import pack, unpack

class ObjectWithStream(object):
    def __init__(self, data=None, endianity='<'):
        self.endianity = endianity
        if None == data:
            self.stream = BytesIO()
        elif isinstance(data, str):
            self.stream = BytesIO.BytesIO(data)
            self.stream.seek(0)
        else:
            self.stream = data
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
        return unpack(self.endianity + 'L', self.stream.read(4))[0]
    def readUInt16(self):
        return unpack(self.endianity + 'H', self.stream.read(2))[0]
    def readUInt8(self):
        return ord(self.stream.read(1))
    def makeUInt32(self, x):
        return pack(self.endianity + 'L', x)
    def makeUInt16(self, x):
        return pack(self.endianity + 'H', x)
    def makeUInt8(self, x):
        return chr(x)
    def writeUInt32(self, x):
        self.stream.write(pack(self.endianity + 'L', x))
    def writeUInt16(self, x):
        self.stream.write(pack(self.endianity + 'H', x))
    def writeUInt8(self, x):
        self.stream.write(chr(x))
    def readMBInt(self):
        continueBit = True
        result = 0
        while continueBit:
            result <<= 7
            nextByte = self.readUInt8()
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
            if '>' == self.endianity:
                nextByte = nextByte[::-1]
        else:
            nextByte = self.stream.read(1)
        while nextByte not in [b'\x00', b'\x00\x00']:
            result += nextByte
            if isUTF16:
                nextByte = self.stream.read(2)
                if '>' == self.endianity:
                    nextByte = nextByte[::-1]
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
    def __init__(self, data=None):
        ObjectWithStream.__init__(self, data, endianity='>')

