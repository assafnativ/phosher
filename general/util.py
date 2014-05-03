
import sys
import struct

def printIfVerbose( text, isVerbose ):
    if isVerbose:
        print text

def DATA( data, base = 0, itemsInRow=0x10 ):
    result = ''
    for i in range(0, len(data), itemsInRow):
        line = '%08X  ' % (i + base)
        line_data = data[i:][:itemsInRow]
        for t in range(len(line_data)):
            if( (0 == (t % 8)) and (t > 0) ):
                line += '- %02X' % ord(line_data[t])
            elif( 0 == (t & 1) ):
                line += '%02X' % ord(line_data[t])
            elif( 1 == (t & 1) ):
                line += '%02X ' % ord(line_data[t])
            
        spacesLeft = 13 + int(itemsInRow * 2.5) + (2 * ((itemsInRow - 1)//8))
        line += ' ' * (spacesLeft - len(line))
        for t in line_data:
            if( t == repr(t)[1] ):
                line += t
            else:
                line += '.'
        line += '\n'
        result += line
    return( result )


def hex2data( h ):
    if h[:2] == '0x':
        return h[2:].decode('hex')
    return h.decode('hex')

def data2hex( d ):
    return d.encode('hex')

def buffDiff( buffers, chunk_size = 1, endianity='=' ):
    if type(buffers) != type([]):
        print('Invalid type')
        return
    l = len(buffers[0])
    for i in buffers:
        if( type(i) == type([]) ):
            for j in i:
                if( len(j) < l ):
                    l = len(j)
        else:
            if( len(i) < l ):
                l = len(i)
    i = 0
    total_diffs = 0
    while l - i >= chunk_size:
        chunks = []
        diff_this_chunk = True
        for buff in buffers:
            if type(buff) == type([]):
                chunk0 = buff[0][i:i+chunk_size]
                for sub_buff in buff:
                    if sub_buff[i:i+chunk_size] != chunk0:
                        diff_this_chunk = False
                        break
                if False == diff_this_chunk:
                    break
                else:
                    chunks.append(chunk0[:])
            else:
                chunks.append( buff[i:i+chunk_size] )

        if True == diff_this_chunk:
            #chunks = map(lambda x:x[i:i+chunk_size], buffers)
            chunk0 = chunks[0]
            for chunk in chunks:
                if chunk != chunk0:
                    if( 1 == chunk_size ):
                        print("Buff diff at {0:X}: ".format(i)),
                        for chunk in chunks:
                            print("{0:02X} ".format(ord(chunk))),
                        print
                    elif( 2 == chunk_size ):
                        print("Buff diff at {0:X}: ".format(i)),
                        for chunk in chunks:
                            print("{0:04X} ".format(struct.unpack(endianity + 'H',chunk)[0])),
                        print
                    elif( 4 == chunk_size ):
                        print("Buff diff at {0:X}: ".format(i)),
                        for chunk in chunks:
                            print("{0:08X} ".format(struct.unpack(endianity + 'L',chunk)[0])),
                        print
                    else:
                        print("Buff diff at {0:X}: ".format(i)),
                        for chunk in chunks:
                            print("\t{0:s}".format(data2hex(chunk))),
                    total_diffs += 1
                    break
        i += chunk_size
    if( 0 == total_diffs ):
        print("Buffers match!")
    else:
        print("Total diffs %d" % total_diffs)

_LAST_TRACEBACK = None
def exceptionLocalsLoad(step=1):
    global _LAST_TRACEBACK
    _LAST_TRACEBACK = sys.last_traceback
    exceptionUp(step)

def exceptionUp(step=1):
    global _LAST_TRACEBACK
    import __main__
    for i in range(step):
        _LAST_TRACEBACK = _LAST_TRACEBACK.tb_next
    frame = _LAST_TRACEBACK.tb_frame
    print("Loading exception locals of file %s, line %d, in %s" % (frame.f_code.co_filename, _LAST_TRACEBACK.tb_lineno, frame.f_code.co_name))
    l = frame.f_locals
    for item in l.keys():
        if not item.startswith('_'):
            #print("Adding: %s" % item)
            setattr(__main__, item, l[item])

