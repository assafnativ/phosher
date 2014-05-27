
from StringIO import StringIO
import sys

def removeTextInBetween(text, start, end):
    pos = text.find(start)
    while -1 != pos:
        endPos = text.find(end, pos)
        if -1 == endPos:
            raise Exception("Can't find closer of %s for %s" % (end, start))
        text = text[:pos] + text[endPos+len(end):]
        pos = text.find(start)
    return text

def clearComments(text):
    return removeTextInBetween(removeTextInBetween(text, '/*', '*/'), '//', '\n')

def getTextInQuotes(text):
    pos = text.find('"')
    if -1 == pos:
        raise Exception("Can't find openning quote")
    pos += 1
    endPos = text.find('"', pos)
    if -1 == pos:
        raise Exception("Can't find closing quote")
    return text[pos:endPos]

def parsePPU(ppu):
    if len(ppu) < 0x100:
        ppu = file(ppu, 'rb').read()

    result = {}
    ppu = clearComments(ppu)
    ppu = ppu.replace('\r', '')
    ppu = ppu.split('\n')

    lineNumber = 0
    while lineNumber < len(ppu):
        line = ppu[lineNumber]
        if '' == line:
            pass
        elif line[0].isdigit():
            pos = line.find(' ')
            if -1 == pos:
                raise Exception("Space not found")
            tagNumber = int(line[:pos], 0)
            tagName = getTextInQuotes(line)
            if 'STATIC COMBOBOX' in line:
                lineNumber += 1
                line = ppu[lineNumber].strip()
                options = {}
                while not line.startswith(';'):
                    if '' == line:
                        pass
                    else:
                        pos = line.find(' ')
                        if -1 == pos:
                            raise Exception("Space for val not found")
                        val = int(line[:pos], 0)
                        explain = getTextInQuotes(line)
                        options[val] = explain
                    lineNumber += 1
                    line = ppu[lineNumber].strip()
            elif 'STATIC CHECKBOX' in line:
                options = {0:'Off', 1:'On'}
            elif 'STATIC EDITFIELD' in line:
                options = None
            else:
                options = None
            result[tagNumber] = (tagName, options)
        lineNumber += 1
    return result
    
def parsePP(pp, ppu):
    if len(pp) < 0x100:
        pp = file(pp, 'rb').read()
    pp = pp.replace('\r', '')
    pp = pp.split('\n')
    pp = pp[4:]
    if pp[0] != 'SET 1':
        raise Exception("PP not formated")
    lineNumber = 1
    while lineNumber < len(pp):
        line = pp[lineNumber]
        if len(line) <= 1:
            pass
        else:
            tagNum, val = [int(x) for x in line.split()]
            if tagNum not in ppu:
                print "Unknown tag %d = %d" % (tagNum, val)
            else:
                name, options = ppu[tagNum]
                if None != options:
                    if val in options:
                        print "TAG(%d): %s = %s" % (tagNum, name, options[val])
                    else:
                        print "TAG(%d): %s = Invalid options %d" % (tagNum, name, val)
                else:
                    print "TAG(%d): %s = %d" % (tagNum, name, val)
        lineNumber += 1


