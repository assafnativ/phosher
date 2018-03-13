import serial

class connect(object):
    def __init__(self, com=None):
        if None == com:
            com = 'COM11'
        self.com = com
        self.s = serial.Serial(com, 14400)
        self.s.timeout = 1
        self.s.write('AT\r\n')
        text = self.serialRead()
        if 'OK' not in text:
            raise Exception("Communication error (%s)" % text)

    def serialRead(self):
        text = ''
        while (not text.endswith('\r\nOK\r\n')) and (not text.endswith('\r\nERROR\r\n')):
            c = self.s.read(1)
            if '' == c:
                break
            text += c
        return text

    def readMemBlock(self, addr):
        self.s.write('AT+WS46=%d\r\n' % addr)
        text = self.serialRead()
        pos = text.find('Mem (')
        if -1 == pos:
            raise Exception("Read fail")
        endPos = text.find(')', pos)
        readAddr = int(text[pos+5:endPos], 16)
        if readAddr != addr:
            raise Exception("Read wrong address %x %x" % (readAddr, addr))
        pos = endPos + 6
        endPos = text.find('\r\n', pos)
        data = text[pos:endPos].decode('hex')
        return data

    def readRange(self, startAddr, endAddr):
        if endAddr <= startAddr:
            raise Exception("Invalid range")
        addr = startAddr
        dump = ''
        while addr < endAddr:
            block = self.readMemBlock(addr)
            addr += len(block)
            dump += block
        return dump

    def readRangeToFile(self, startAddr, endAddr, fileName):
        if endAddr <= startAddr:
            raise Exception("Invalid range")
        with open(fileName, 'wb') as output:
            addr = startAddr
            while addr < endAddr:
                block = self.readMemBlock(addr)
                addr += len(block)
                output.write(block)
