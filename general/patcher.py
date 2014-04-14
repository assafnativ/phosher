
import time
from struct import pack, unpack
from .utile import *
from ..fat16.patcher import *

class Patcher(object):
    def __init__(self):
        pass
    def patchBuffer( self, plain, offset, newValue, isVerbose=True ):
        if not isinstance(newValue, str):
            raise Exception("Patch new vlaue should be binary string")
        bufferLen = len(newValue)
        printIfVerbos( 'Patching buffer at offset 0x%x of length 0x%x' % (offset, bufferLen), isVerbose )
        printIfVerbos( 'Old value 0x%s' % plain[offset:offset+bufferLen].encode('hex'), isVerbose )
        plain = plain[:offset] + newValue + plain[offset+bufferLen:]
        printIfVerbos( 'New value 0x%s' % plain[offset:offset+bufferLen].encode('hex'), isVerbose )
        return plain

def patchSource( source, lineNumber, original, patch, isVerbose=True ):
    lineNumber -= 1
    lines = source.split('\n')
    if original not in lines[lineNumber]:
        raise Exception("Original not found")
    lines = lines[:lineNumber] + \
            [lines[lineNumber].replace(original, patch)] + \
            lines[lineNumber+1:] 
    return '\n'.join(lines)

def setPPMPatches(ppm, ppmPatches):
    for path, newValue in ppmPatches:
        if 'version' == path:
            ppm.version = newValue
        else:
            path = path.split('.')
            for section in ppm.sections:
                if section.name == path[0]:
                    break
            else:
                raise Exception("Can't find %s section" % path[0])
            for subSection in section.subSections:
                if subSection.name == path[1]:
                    break
            else:
                raise Exception("Can't find %s subSection" % path[1])
            if 'TEXT' == path[0]:
                subSection.texts[int(path[2])] = newValue
            elif 'ANIM' == path[0]:
                targetIndex = int(path[2], 0)
                for i, (index, unk, unk2, data) in enumerate(subSection.animations):
                    if index == targetIndex:
                        break
                else:
                    raise Exception("Can't find animation with index 0x%x" % targetIndex)
                subSection.animations[i] = (index, unk, unk2, newData)

def patchImage(imageFile, fat16patches, isXGold=False):
    startTime = time.time()
    raw = file(imageFile, 'rb').read()
    version = unpack('>H', raw[0x46:0x48])[0]
    pos = imageFile.rfind('.')
    if -1 == pos:
        pos = len(imageFile)
    new_name = imageFile[:pos] + '.patched' + imageFile[pos:]
    blobs = parseXGoldPack(imageFile)
    data = None
    for i, (t, d) in enumerate(blobs):
        if t == 0xc:
            if None != data:
                raise Exception("More than one FAT16 blob")
            data = d
            blobIndex = i
    pos = data.find('\xeb\xfe\x90')
    if -1 == pos or pos > 0x80:
        raise Exception("Fat16 start error")
    fat16raw = data[pos:]
    blobHeader = data[:pos]
    fat16 = FAT16(fat16raw, isVerbose=False, isXGold=isXGold)
    patchFat16(fat16, fat16patches)
    fat16raw = fat16.make()
    file(new_name + '.fat16.ima', 'wb').write(fat16raw)
    newBlob = blobHeader + fat16raw
    blobs[blobIndex] = (0xc, newBlob)
    print "Writing result to %s" % new_name
    file(new_name, 'wb').write(makeXGoldPack(blobs, version))
    print "Done, it took %d sec" % (time.time() - startTime)
    return new_name
   
def patchPPM(ppmFile, ppmPatches):
    startTime = time.time()
    ppm = PPM()
    ppm.parsePPM(ppmFile, containerType='XGold')
    setPPMPatches(ppm, ppmPatches)
    pos = ppmFile.rfind('.')
    if -1 == pos:
        pos = len(imageFile)
    new_name = ppmFile[:pos] + '.patched' + ppmFile[pos:]
    print "Writing result to %s" % new_name
    ppm.make(new_name, containerType='XGold')
    print "Done, it took %d sec" % (time.time() - startTime)
    return new_name

