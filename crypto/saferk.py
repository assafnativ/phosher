K64_DEFAULT_NUM_ROUNDS = 6
K128_DEFAULT_NUM_ROUNDS = 10
SK64_DEFAULT_NUM_ROUNDS = 8
SK128_DEFAULT_NUM_ROUNDS = 10

def ROLByte(x, bits):
    bits %= 8
    return ((x << bits) | ((x & 0xff) >> (8 - bits))) & 0xff

class Safer(object):
    def __init__(self):
        self.BLOCK_LEN = 8
        self.MAX_ROUNDS = 13
        # sbox  AKA exp table
        # rsbox AKA log table
        self.sbox = [int((45 ** i) % 257 & 0xff) for i in range(0x100)]
        self.rsbox = [0] * 0x100
        for i in range(0x100):
            self.rsbox[self.sbox[i]] = i
        # Validate sbox
        for i in range(0x100):
            if i != self.rsbox[self.sbox[i]]:
                raise Exception("Init error")
        self.operationsSet1 = [\
                int.__xor__, int.__add__, int.__add__, int.__xor__,
                int.__xor__, int.__add__, int.__add__, int.__xor__ ]
        self.invOperationsSet1 = [\
                int.__xor__, int.__sub__, int.__sub__, int.__xor__,
                int.__xor__, int.__sub__, int.__sub__, int.__xor__]
        self.invOperationsSet1Tag = [\
                int.__sub__, int.__xor__, int.__xor__, int.__sub__,
                int.__sub__, int.__xor__, int.__xor__, int.__sub__]
        def sboxPluse(x, y):
            return self.sbox[x] + y
        def rsboxXor(x, y):
            return self.rsbox[x] ^ y
        def sboxMinus(x, y):
            return self.sbox[x] - y
        self.operationsSet2 = [
                sboxPluse, rsboxXor,
                rsboxXor, sboxPluse,
                sboxPluse, rsboxXor,
                rsboxXor, sboxPluse ]
        self.invOperationsSet2 = [
                rsboxXor, sboxMinus,
                sboxMinus, rsboxXor,
                rsboxXor, sboxMinus,
                sboxMinus, rsboxXor ]
        def PHT(x, y):
            y += x
            x += y
            return (x & 0xff, y & 0xff)
        self.PHT = PHT
        def IPHT(x, y):
            x -= y
            y -= x
            return (x & 0xff, y & 0xff)
        self.IPHT = IPHT

    def expandUserKey(self, userKey, numRounds, strengthened):
        if isinstance(userKey, str):
            userKey = map(ord, userKey)
        keyA = [0] * (self.BLOCK_LEN + 1)
        keyB = [0] * (self.BLOCK_LEN + 1)
        numRounds = min(numRounds, self.MAX_ROUNDS)
        key = [numRounds]
        keyA[-1] = 0
        keyB[-1] = 0
        keyPos = 0
        for i in range(self.BLOCK_LEN):
            key.append(userKey[i])
            keyA[i] = ROLByte(userKey[i], 5)
            keyB[i] = key[-1]
            keyA[-1] ^= keyA[i]
            keyB[-1] ^= keyB[i]

        for i in range(numRounds):
            keyA = [ROLByte(x, 6) for x in keyA[:-1]] + [keyA[-1]]
            keyB = [ROLByte(x, 6) for x in keyB[:-1]] + [keyB[-1]]
            for j in range(self.BLOCK_LEN):
                if strengthened:
                    key.append(keyA[(j + 2 * i - 1) % len(keyA)])
                else:
                    key.append(keyA[j])
                key[-1] += self.sbox[self.sbox[18 * i + j + 1]]
                key[-1] &= 0xff
            for j in range(self.BLOCK_LEN):
                if strengthened:
                    key.append(keyB[(j + 2 * i) % len(keyB)])
                else:
                    key.append(keyB[j])
                key[-1] += self.sbox[self.sbox[18 * i + j + 10]]
                key[-1] &= 0xff
        self.key = key

    def encryptBlock(self, block):
        block = map(ord, block)
        rounds = min(self.key[0], self.MAX_ROUNDS)
        keyPos = 1
        for r in range(rounds):
            keyPart = self.key[keyPos:keyPos+len(block)]
            block = [int(op(x, k) & 0xff) for op, x, k in zip(self.operationsSet1, block, keyPart)]
            keyPos += len(block)
            keyPart = self.key[keyPos:keyPos+len(block)]
            block = [int(op(x, k) & 0xff) for op, x, k in zip(self.operationsSet2, block, keyPart)]
            keyPos += len(block)

            block[0], block[1] = self.PHT(block[0], block[1])
            block[2], block[3] = self.PHT(block[2], block[3])
            block[4], block[5] = self.PHT(block[4], block[5])
            block[6], block[7] = self.PHT(block[6], block[7])

            block[0], block[2] = self.PHT(block[0], block[2])
            block[4], block[6] = self.PHT(block[4], block[6])
            block[1], block[3] = self.PHT(block[1], block[3])
            block[5], block[7] = self.PHT(block[5], block[7])

            block[0], block[4] = self.PHT(block[0], block[4])
            block[1], block[5] = self.PHT(block[1], block[5])
            block[2], block[6] = self.PHT(block[2], block[6])
            block[3], block[7] = self.PHT(block[3], block[7])

            block = [
                    block[0], block[4], block[1], block[5],
                    block[2], block[6], block[3], block[7]]
        keyPart = self.key[keyPos:keyPos+len(block)]
        block = [int(op(x, k) & 0xff) for op, x, k in zip(self.operationsSet1, block, keyPart)]
        return ''.join(map(chr, block))

    def decryptBlock(self, block):
        block = map(ord, block)
        rounds = min(self.key[0], self.MAX_ROUNDS)
        keyPos = len(self.key)
        keyPart = self.key[keyPos-len(block):keyPos]
        block = [int(op(x, k) & 0xff) for op, x, k in zip(self.invOperationsSet1, block, keyPart)]
        keyPos -= len(block)
        for r in range(rounds):
            block = [
                    block[0], block[2], block[4], block[6],
                    block[1], block[3], block[5], block[7]]

            block[0], block[4] = self.IPHT(block[0], block[4])
            block[1], block[5] = self.IPHT(block[1], block[5])
            block[2], block[6] = self.IPHT(block[2], block[6])
            block[3], block[7] = self.IPHT(block[3], block[7])

            block[0], block[2] = self.IPHT(block[0], block[2])
            block[4], block[6] = self.IPHT(block[4], block[6])
            block[1], block[3] = self.IPHT(block[1], block[3])
            block[5], block[7] = self.IPHT(block[5], block[7])

            block[0], block[1] = self.IPHT(block[0], block[1])
            block[2], block[3] = self.IPHT(block[2], block[3])
            block[4], block[5] = self.IPHT(block[4], block[5])
            block[6], block[7] = self.IPHT(block[6], block[7])

            keyPart = self.key[keyPos-len(block):keyPos]
            block = [int(op(x, k) & 0xff) for op, x, k in zip(self.invOperationsSet1Tag, block, keyPart)]
            keyPos -= len(block)
            keyPart = self.key[keyPos-len(block):keyPos]
            block = [int(op(x, k) & 0xff) for op, x, k in zip(self.invOperationsSet2, block, keyPart)]
            keyPos -= len(block)
        return ''.join(map(chr, block))

