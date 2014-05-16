
import os
import sys
import shutil
from optparse import OptionParser

from phosher.general.util import *
from phosher.general.objectWithStream import *

class EXTENSION(object):
    def __init__(self):
        pass

class WBXML(ObjectWithStream):
    TOKENS = {
            0x00: 'SWITCH_PAGE',
            0x01: 'END',
            0x02: 'ENTITY',
            0x03: 'STR_I',
            0x04: 'LITERAL',
            0x40: 'EXT_I_0',
            0x41: 'EXT_I_1',
            0x42: 'EXT_I_2',
            0x43: 'PI',
            0x44: 'LITERAL_C',
            0x80: 'EXT_T_0',
            0x81: 'EXT_T_1',
            0x82: 'EXT_T_2',
            0x83: 'STR_T',
            0x84: 'LITERAL_A',
            0xC0: 'EXT_0',
            0xC1: 'EXT_1',
            0xC2: 'EXT_2',
            0xC3: 'OPAQUE',
            0xC4: 'LITERAL_AC'}

    PUBLIC_ID = {
            0 : 'String table index', \
            1 : 'Unknown', \
            2 : "-//WAPFORUM//DTD WML 1.0//EN", \
            3 : "-//WAPFORUM//DTD WTA 1.0//EN", \
            4 : "-//WAPFORUM//DTD WML 1.1//EN", \
            5 : "-//WAPFORUM//DTD SI 1.0//EN", \
            6 : "-//WAPFORUM//DTD SL 1.0//EN", \
            7 : "-//WAPFORUM//DTD CO 1.0//EN", \
            8 : "-//WAPFORUM//DTD CHANNEL 1.1//EN", \
            9 : "-//WAPFORUM//DTD WML 1.2//EN", \
            10 : "-//WAPFORUM//DTD WML 1.3//EN", \
            11 : "-//WAPFORUM//DTD PROV 1.0//EN", \
            12 : "-//WAPFORUM//DTD WTA-WML 1.2//EN", \
            13 : "-//WAPFORUM//DTD EMN 1.0//EN", \
            14 : "-//OMA//DTD DRMREL 1.0//EN", \
            15 : "-//WIRELESSVILLAGE//DTD CSP 1.0//EN", \
            16 : "-//WIRELESSVILLAGE//DTD CSP 1.1//EN", \
            17 : "-//OMA//DTD WV-CSP 1.2//EN", \
            18 : "-//OMA//DTD IMPS-CSP 1.3//EN", \
            19 : "-//OMA//DRM 2.1//EN", \
            20 : "-//OMA//SRM 1.0//EN", \
            21 : "-//OMA//DCD 1.0//EN", \
            22 : "-//OMA//DTD DS-DataObjectEmail 1.2//EN", \
            23 : "-//OMA//DTD DS-DataObjectFolder 1.2//EN", \
            24 : "-//OMA//DTD DS-DataObjectFile 1.2//EN", \
            0x0FD3 : "-//SYNCML//DTD SyncML 1.1//EN", \
            0x0FD4 : "-//SYNCML//DTD DevInf 1.1//EN", \
            0x200012 : "Nokia" }

    VALUES_DB = {
            "Nokia" : {
                'tag' : {
                    0 : {
                        0x22 : "SETTINGS",
                        0x23 : "KEY",
                        0x24 : "ITEM", 
                        0x25 : "VERSIONINFO",
                        0x26 : "PROJECT"
                    },
                },
                'attrvalue' : {
                    0 : {
                        0x06 : 'LEVEL="BASELINE"',
                        0x07 : 'LEVEL="PRODUCT_FAMILY"',
                        0x08 : 'LEVEL="PRODUCT"',
                        0x09 : 'LEVEL="REGION"',
                        0x0a : 'LEVEL="COUNTRY"',
                        0x0b : 'LEVEL="VARIANT"',
                        0x0d : 'LEVEL="BOOLEAN"',
                        0x0e : 'LEVEL="STRING"',
                        0x0f : 'LEVEL="INTEGER"',
                        0x10 : 'LEVEL="FLOAT"',
                        0x11 : 'LEVEL="PATH"',
                        0x12 : 'ID',
                        0x13 : 'NAME',
                        0x15 : 'VERSION',
                        0x17 : 'VALUE',
                    },
                },
            },
        }

    def __init__(self, data, isVerbose=False):
        ObjectWithStream.__init__(self, data)
        self.TOKENS_REVESRE = dict([(y, x) for x, y in self.TOKENS.items()])
        self.isVerbose = isVerbose
        if len(data) < 0x100:
            data = file(data, 'rb').read()
        self.dataLength = len(data)
        self.parse()

    def parseToken(self, codePage=0, isAttrib=False):
        result = []
        offset = self.tell()
        tag = self.read(1)
        if len(tag) == 0:
            return ('END', None, None, None, offset)
        tag = ord(tag)
        self.currentCodePage = codePage
        if tag in self.TOKENS:
            token = self.TOKENS[tag]
            if 'STR_I' == token:
                val = self.readString()
            elif 'STR_T' == token:
                tableOffset = self.readMBInt()
                val = self.stringFromTable(tableOffset)
            elif token in ['EXT_T_0', 'EXT_T_1', 'EXT_T_2']:
                val = str(self.readMBInt())
            elif token in ['EXT_I_0', 'EXT_I_1', 'EXT_I_2']:
                val = self.stringFromTable(data)
            elif token in ['EXT_0', 'EXT_1', 'EXT_2']:
                val = read(1)
            elif 'ENTITY' == token:
                val = 'ENTITY(%d)' % self.readMBInt()
            elif 'PI' == token:
                val = repr(parseToken(codePage=self.currentCodePage))
            elif token.startswith('LITERAL'):
                val = 'LITERAL(' + str(self.readMBInt()) + ')'
            elif 'SWITCH_PAGE' == token:
                self.currentCodePage = self.readUInt8()
                val = 'SWITCH_PAGE(%d)' % (self.currentCodePage)
            elif 'END' == token:
                val = None
            else:
                raise Exception("Don't know what to do with token %s" % token)
            return (token, None, val, None, offset)
        tagId = tag & 0x3f
        tagHasElement = (0 != (tag & 0x40))
        tagHasAttrib  = (0 != (tag & 0x80))
        attribs = []
        if tagHasAttrib:
            nextToken = self.parseToken(codePage=self.currentCodePage, isAttrib=True)
            while 'END' != nextToken[0]:
                attribs.append(nextToken)
                nextToken = self.parseToken(codePage=self.currentCodePage, isAttrib=True)
        content = []
        if tagHasElement:
            nextToken = self.parseToken(codePage=self.currentCodePage)
            while 'END' != nextToken[0]:
                content.append(nextToken)
                nextToken = self.parseToken(codePage=self.currentCodePage)
        token = tagId
        val = self.resolveFromDB(tagId, isAttrib)
        return (token, attribs, val, content, offset)

    def resolveFromDB(self, tagId, isAttrib):
        if isAttrib:
            subDic = "attrvalue"
        else:
            subDic = "tag"
        if self.publicIdName in self.VALUES_DB:
            db = self.VALUES_DB[self.publicIdName][subDic]
        else:
            return str(tagId)
        if self.currentCodePage in db:
            db = db[self.currentCodePage]
        else:
            return str(tagId)
        return db.get(tagId, str(tagId))

    def parse(self):
        self.version = self.readUInt8()
        self.publicId = self.readMBInt()
        self.publicIdName = self.PUBLIC_ID.get(self.publicId, '?')
        printIfVerbose('wbxml version: %x' % self.version, self.isVerbose)
        printIfVerbose('PublicId: %x (%s)' % (self.publicId, self.publicIdName), self.isVerbose)
        self.charset = self.readMBInt()
        printIfVerbose('Charset: 0x%02x (0x6a = UTF-8)' % self.charset, self.isVerbose)
        self.strtbl_len = self.readMBInt()
        self.strtbl_raw = self.read(self.strtbl_len)
        self.strtbl = ObjectWithStream(self.strtbl_raw)
        if self.strtbl_len > 0:
            printIfVerbose("Has strtbl", self.isVerbose)
        else:
            printIfVerbose("No strtbl", self.isVerbose)
        self.tags = []
        printIfVerbose("Start reading tokens from offset 0x%x" % self.tell(), self.isVerbose)
        while self.tell() < self.dataLength:
            self.tags.append(self.parseToken())

    def build(self, isVerbose=False):
        # This function requires more work
        result = ObjectWithStream()
        result.writeUInt8(self.version)
        result.writeMBInt(self.publicId)
        result.writeMBInt(self.charset)
        result.writeMBInt(self.strtbl_len)
        result.write(self.strtbl_raw)
        self._build(result, self.tags)
        # First level dont have a ENDing token
        return result.getRawData()[:-1]

    def getTag(self, path):
        tags = (None, None, None, self.tags)
        for x in path:
            tags = tags[3][x]
        return tags

    def getTagId(self, path):
        return getTag(path)[0]
    def getAttrib(self, path):
        return getTag(path)[1]
    def getVal(self, path):
        return getTag(path)[2]
    def getContent(self, path):
        return getTag(path)[3]

    def setTag(self, path, tagVal):
        tags = (None, None, None, self.tags)
        for x in path[:-1]:
            tags = tags[3][x]
        tags[3][path[-1]] = tagVal

    def patchTag(self, path, attrib=None, content=None, val=None):
        tag = self.getTag(path)
        tagVal = list(tag)
        if None != attrib:
            tagVal[1] = attrib
        if None != content:
            tagVal[3] = content
        if None != val:
            tagVal[2] = val
        self.setTag(path, tuple(tagVal))

    def _build(self, result, tags, isAttrib=False, currentCodePage=0):
        if 0 == len(tags):
            raise Exception("Empty tags")
        for tagId, attrbis, val, content, _ in tags:
            tagCode = tagId
            if tagCode in self.TOKENS_REVESRE:
                token = tagCode
                tagCode = self.TOKENS_REVESRE[tagCode]
                result.writeUInt8(tagCode)
                if 'STR_I' == token:
                    result.write(val + '\x00')
                elif 'STR_T' == token:
                    if val == self.stringFromTable(0):
                        tableOffset = 0
                    else:
                        target = '\x00' + val + '\x00'
                        if target in self.strtbl_raw:
                            tableOffset = self.strtbl_raw.index(target) + 1
                        else:
                            raise Exception("Can't find string in table")
                    result.writeMBInt(tableOffset)
                elif token in ['EXT_T_0', 'EXT_T_1', 'EXT_T_2']:
                    result.writeMBInt(int(val, 0))
                elif token in ['EXT_I_0', 'EXT_I_1', 'EXT_I_2']:
                    raise Exception("EXT_I token not implemented")
                elif token in ['EXT_0', 'EXT_1', 'EXT_2']:
                    result.write(val)
                elif 'ENTITY' == token:
                    result.writeMBInt(val)
                elif 'PI' == token:
                    # Only one token, but _build works with lists
                    raise Exception("PI token not implemented")
                elif token.startswith('LITERAL'):
                    val = int(val[val.find('(')+1:val.find(')')])
                    result.writeMBInt(val)
                elif 'SWITCH_PAGE' == token:
                    codePage = int(val[val.find('(')+1:val.find(')')])
                    result.writeUInt8(codePage)
                elif 'END' == token:
                    pass
                else:
                    raise Exception("Don't know what to do with token %s" % token)
            else:
                if None != content and 0 < len(content):
                    tagCode |= 0x40
                if None != attrbis and 0 < len(attrbis):
                    tagCode |= 0x80
                result.writeUInt8(tagCode)
                if 0 != (tagCode & 0x80):
                    self._build(result, attrbis, False, currentCodePage)
                if 0 != (tagCode & 0x40):
                    self._build(result, content, True, currentCodePage)
        # Write END token
        result.writeUInt8(1)

    def stringFromTable(self, offset):
        self.strtbl.seek(offset, 0)
        return self.strtbl.readString()

    def display(self, tags=None, path=None):
        if None == tags:
            tags = self.tags
        if None == path:
            path = []
        result = ''
        for i, (tagId, attribs, val, content, fileOffset) in enumerate(tags):
            result += '\n'
            result += '@0x%05x ' % fileOffset
            result += '.'.join([str(x) for x in path + [i]])
            result += '    '
            result += repr(val)[1:-1]
            if None != attribs and len(attribs) > 0:
                result += ' {'
                for attrib in attribs:
                    result += repr(attrib[2])[1:-1]
                    result += ' '
                result += '}'
            if None != content and len(content) > 0:
                result += self.display(content, path + [i])
        return result

def main():
    userOptions = OptionParser()
    userOptions.add_option("-p", "--patches",   dest="patchesFile", type="string", help="Python scriptin that defines global var PATCHES. The file would be executed!")
    userOptions.add_option("-i", "--input",     dest="inputFile",   type="string", help="WBXML file. It is also possible to set a global INPUT_FILE var in the PATCHES file")
    userOptions.add_option("-o", "--output",    dest="outputFile",  type="string", help="New WBXML file. If not set the output file is dervid from the input file name")
    userOptions.add_option("-t", "--text",      dest="isText",      action="store_true", help="Output readable version of the WBXML")
    userOptions.add_option("-v", "--verbose",   dest="isVerbose",   action="store_true", help="Set verbose output on")
    userOptions.set_defaults(inputFile=None, outputFile=None, isVerbose=False, isText=False)
    (options, args) = userOptions.parse_args(sys.argv[1:])
    patchesFile = options.patchesFile
    inputFile   = options.inputFile
    outputFile  = options.outputFile
    isText      = options.isText
    isVerbose   = options.isVerbose
    PATCHES, patchesDefines = loadPatchesFromFile(patchesFile, userOptions, isVerbose)
    inputFile = cmdLineInputFile(patchesDefines, inputFile, userOptions)
    outputFile = cmdLineOutputFile(patchesDefines, outputFile, inputFile)

    data = file(inputFile, 'rb').read()
    wbxml = WBXML(data, isVerbose=isVerbose)
    if None != patchesFile:
        for patch in PATCHES:
            wbxml.patchTag(*patch)
    if isText:
        result = wbxml.display()
    else:
        result = wbxml.build()
    file(outputFile, 'wb').write(result)

if __name__ == "__main__":
    main()
