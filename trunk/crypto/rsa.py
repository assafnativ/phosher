
import os
from glob import glob
from ..general.util import *

class RSA(object):
    def __init__(self):
        pass

    def findOneOf(self, data, oldPos, dataToSearch):
        pos = len(data)
        for x in dataToSearch:
            newPos = data.find(x, oldPos)
            if newPos != -1 and newPos < pos:
                pos = newPos
        if len(data) == pos:
            return -1
        return pos

    def findPublicKeys(self, fname):
        headers = [
                '\x00\x04\x00\x00\x03\x00\x00\x00', \
                '\x00\x04\x00\x00\x01\x00\x01\x00' ]
        inFile = file(fname, 'rb')
        inFile.seek(0, 2)
        fileSize = inFile.tell()
        inFile.seek(0, 0)
        keys = []
        while inFile.tell() < fileSize:
            filePos = inFile.tell()
            if 0x88 < filePos:
                inFile.seek(filePos - 0x88, 0)
            data = inFile.read(0x100000)    # 1 MB at a time
            pos = self.findOneOf(data, 0, headers)
            while -1 != pos:
                key = data[pos+0x8:pos+0x88]
                if len(key) != 0x80:
                    # Get this one on the next chunk
                    break
                key = key[::-1]
                key = int(key.encode('hex'), 16)
                isKey = True
                for prime in [2, 3, 5, 7, 11, 13, 17, 19, 29, 53, 0x10001]:
                    if 0 == (key % prime):
                        # Too easy to break, very unlikly
                        isKey = False
                        break
                if isKey:
                    # Just one more check
                    hexKey = '%x' % key
                    if hexKey.count('0') < (len(hexKey) / 4):
                        keys.append(key)
                pos = self.findOneOf(data, pos + 1, headers)
        return keys

    def collectKeysFromFiles(self, filesPattern, isRecursive=False, isVerbose=False):
        self.done = []
        self.allKeys = {}
        self._collectKeysFromFiles(filesPattern, isRecursive=isRecursive, isVerbose=isVerbose)
        return self.allKeys

    def _collectKeysFromFiles(self, filesPattern, isRecursive=False, isVerbose=False):
        for fname in glob(filesPattern):
            if fname in self.done:
                continue
            self.done.append(fname)
            if isRecursive and os.path.isdir(fname):
                self._collectKeysFromFiles(fname + '\\*', isRecursive=isRecursive, isVerbose=isVerbose)
            elif os.path.isfile(fname):
                printIfVerbose("Scanning file %s" % fname, isVerbose)
                newKeys = self.findPublicKeys(fname)
                for key in newKeys:
                    if key not in self.allKeys.keys():
                        self.allKeys[key] = [fname]
                        printIfVerbose("Found key: %x in %s" % (key, fname), isVerbose)
                    else:
                        self.allKeys[key].append(fname)

    def decryptRsaBlock(self, block, key, e=3, removePad=True):
        blockInt = int(block.encode('hex'), 16)
        plainInt = pow(blockInt, e, key)
        plain = hex(plainInt)[2:]
        if plain[-1] == 'L' or plain[-1] == 'l':
            plain = plain[:-1]
        if 0 != (len(plain) % 2):
            plain = '0' + plain
        plain = plain.decode('hex')
        if 0x80 != len(plain):
            plain = ('\x00' * (0x80 - len(plain))) + plain
        if not removePad:
            return plain
        if '\x00\x02' != plain[:2]:
            return None
        pos = 2
        while '\xff' == plain[pos]:
            pos += 1
        if pos < 0x20:
            return None
        return plain[pos:]

    def decryptRsaBlockTryAllKeys(self, block, keys=None, removePad=True):
        if None == keys:
            keys = self.allKeys
        for key in keys:
            for e in [3, 7, 0x10001]:
                plain = self.decryptRsaBlock(block, key, e, removePad=removePad)
                if None != plain:
                    return plain
        return None


