
from ..general.util import printIfVerbose
from glob import glob
from fractions import gcd
import math
import gmpy2

class rsaResearch(object):
    def checkSmallPrimes(self, keys, time_per_key=5):
        if not isinstance(keys, (tuple, list)):
            keys = [keys]
        c = 10
        a0 = 1
        for key in keys:
            start_time = time.time()
            a1 = (a0**2  + c) % key
            a2 = (a1**2 + c) % key
            while (time.time() - start_time) < time_per_key:
                if gcd(key, abs(a2-a1)) != 1:
                    print "Found small prime!!!"
                    print a1
                    print a2
                    print a2 - a1
                    print key
                a1 = (a1 ** 2 + c) % key
                a2 = (a2 ** 2 + c) % key
                a2 = (a2 ** 2 + c) % key

    def gcdAttack(self, keys, primes=None):
        if None == primes:
            primes = []
        all_keys = 1
        for key in keys:
            all_keys *= key
        all_primes = 1
        for prime in primes:
            all_primes *= prime
        gcd_result = gcd(all_keys, all_primes)
        if 1 != gcd_result:
            print 'GCD with primes', gcd_result
        mid = len(keys) // 2
        self.gcdAttackTwoGroups(keys[:mid], keys[mid:])

    def gcdAttackTwoGroups(self, keys1, keys2):
        if len(keys1) == 0 or len(keys2) == 0:
            return
        all_keys1 = 1
        for key in keys1:
            all_keys1 *= key
        all_keys2 = 1
        for key in keys2:
            all_keys2 *= key
        gcd_result = gcd(all_keys1, all_keys2)
        if 1 != gcd_result:
            print 'GCD of', gcd_result, 'found!!!'
        mid = len(keys1) // 2
        self.gcdAttackTwoGroups(keys1[:mid], keys1[mid:])
        mid = len(keys2) // 2
        self.gcdAttackTwoGroups(keys2[:mid], keys2[mid:])

    def checkPQDistance(self, keys):
        if not isinstance(keys, (tuple, list)):
            keys = [keys]
        ctx = gmpy2.get_context()
        ctx.precision = 5000
        ctx.round = gmpy2.RoundDown
        ctx.real_round = gmpy2.RoundDown
        gmpy2.set_context(ctx)
        for key in keys:
            gmpy_key = gmpy2.mpfr(key)
            skey = int(gmpy2.sqrt(gmpy_key))
            skey2 = skey ** 2
            if (skey2 > key) or (((skey + 1) ** 2) < key):
                print skey2
                print (skey+1)**2
                raise Exception("WTF")
            bits = int(gmpy2.log2(key - skey2))
            if bits < 480:
                print '%d Has p, q distance of %d bits' % (key, bits)

    def entropy(self, data):
        data = [ord(x) for x in data]
        alphabet = list(Set(data))
        length = len(data)
        freqList = [float(data.count(x)) / length for x in alphabet]
        ent = 0.0
        for freq in freqList:
            ent = ent + freq * math.log(freq, 2)
        ent = -ent
        return int(math.ceil(ent))

    def findBlockOfRandom(self, data, block_size=0x80):
        result = []
        if len(data) < 0x100:
            data = file(data, 'rb').read()
        zeros_length = 8
        avrg_for_random = (float(block_size) / float(0x100)) * 8.0
        #print "Using avrg for random of", avrg_for_random
        for pos in range(0, len(data) - (block_size + zeros_length + zeros_length), 1):
            zeroStart = True
            for i in range(zeros_length):
                if '\x00' != data[pos+i]:
                    zeroStart = False
                    break
            if zeroStart:
                zeroEnd = True
                for i in range(zeros_length):
                    if '\x00' != data[pos++zeros_length+block_size+i]:
                        zeroEnd = False
                        break
                if zeroEnd:
                    block = data[pos+zeros_length:pos+zeros_length+block_size]
                    if self.entropy(block) > 6:
                        result.append(block)
        return block

    def findAndDecryptRandomBlocks(self, data, keys, block_size=0x80, is_verbose=True):
        if len(data) < 0x100:
            data = file(data, 'rb').read()
        blocks = list(self.findBlockOfRandom(data, block_size=block_size))
        printIfVerbose("Found %d blocks of random" % len(blocks), is_verbose)
        plains = []
        for block in blocks:
            plain = decrypt_rsa_try_all_keys(block, keys)
            if None != plain:
                printIfVerbose("Block at 0x%x decrypted" % (data.find(block)), is_verbose)
                printIfVerbose(DATA(plain), is_verbose)
                plains.append(plain)
        return plains


