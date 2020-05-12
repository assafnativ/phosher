
class FAT_DELETE(object):
    def __init__(self, ignoreMissing=False):
        self.ignoreMissing = ignoreMissing

class FAT_NEW_DATA(object):
    def __init__(self, new_data, display=None):
        self.new_data = new_data
        self.display = display

class FAT_NEW_FILE(object):
    def __init__(self, src_file, attrib=0x25):
        self.src_file = src_file
        self.attrib = attrib

class FAT_NEW_DIR(object):
    def __init__(self, dir_name, attrib=0x35, createAlways=False):
        self.dir_name = dir_name
        self.attrib = attrib
        self.createAlways = createAlways

class FAT_PATCH(object):
    def __init__(self, offset, new_value, old_value=None):
        self.offset = offset
        self.new_value = new_value
        self.old_value = old_value

class FAT_SET_ATTRIB(object):
    def __init__(self, new_attrib):
        self.new_attrib = new_attrib

class FAT_FIX_JAD(object):
    def __init__(self):
        pass

class FAT_MAKE_LINK_TO_FILE(object):
    def __init__(self, dst, prefixData, attrib=0x25):
        self.dst = dst
        self.prefixData = prefixData
        self.attrib = attrib

class FAT_MAKE_LINK_TO_DIR(object):
    def __init__(self, dst, attrib=0x35):
        self.dst = dst
        self.attrib = attrib

class Fat16Patcher(object):
    def __init__(self, fat16):
        self.fat16 = fat16
    def splitDirNameFname(self, path):
        dir_path = path.replace('\\', '/')
        pos = dir_path.rfind('/')
        fname = dir_path[pos+1:]
        dir_path = dir_path[:pos]
        return (dir_path, fname)
    def patch(self, patches):
        fat16 = self.fat16
        for path, patch_list in patches:
            if not isinstance(patch_list, list):
                patch_list = [patch_list]
            for patch in patch_list:
                if isinstance(patch, FAT_DELETE):
                    try:
                        fat16.rmfile(path)
                    except Exception as e:
                        print("File %s not exists" % path)
                        if not patch.ignoreMissing:
                            raise e
                elif isinstance(patch, FAT_NEW_DATA):
                    old_data = fat16.readFile(path)
                    fat16.writeFile(path, patch.new_data)
                    if None != patch.display:
                        patch.display(old_data, new_data)
                elif isinstance(patch, FAT_NEW_FILE):
                    data = file(patch.src_file, 'rb').read()
                    dir_path, fname = self.splitDirNameFname(path)
                    if dir_path not in ['/', '\\', '']:
                        containingFolder = fat16.getFileObj(dir_path)
                        if None == containingFolder:
                            raise Exception("Path: %s not found" % dir_path)
                        creationMicro   = containingFolder.creationMicro
                        creationTime    = containingFolder.creationTime
                        creationDate    = containingFolder.creationDate
                        accessDate      = containingFolder.accessDate
                        updateTime      = containingFolder.updateTime
                        updateDate      = containingFolder.updateDate
                    else:
                        creationMicro   = 0
                        creationTime    = 0
                        creationDate    = 0
                        accessDate      = 0
                        updateTime      = 0
                        updateDate      = 0

                    fat16.createFile(path, patch.attrib, \
                            creationMicro=creationMicro, \
                            creationTime=creationTime, \
                            creationDate=creationDate, \
                            accessDate=accessDate, \
                            updateTime=updateTime, \
                            updateDate=updateDate )
                    fat16.writeFile(path, data)
                elif isinstance(patch, FAT_NEW_DIR):
                    dir_path, fname = self.splitDirNameFname(path)
                    if dir_path not in ['\\', '/', '']:
                        containingFolder = fat16.getFileObj(dir_path)
                        if None == containingFolder:
                            raise Exception("Failed to find parent folder for %s (%s)" % (path, dir_path))
                        creationMicro   = containingFolder.creationMicro
                        creationTime    = containingFolder.creationTime
                        creationDate    = containingFolder.creationDate
                        accessDate      = containingFolder.accessDate
                        updateTime      = containingFolder.updateTime
                        updateDate      = containingFolder.updateDate
                    else:
                        creationMicro   = 0
                        creationTime    = 0
                        creationDate    = 0
                        accessDate      = 0
                        updateTime      = 0
                        updateDate      = 0

                    if not patch.createAlways:
                        isExists = fat16.getFileObj(path)
                        if (None != isExists):
                            raise Exception("Dir %s already exists!" % path)
                    patch.attrib |= 0x10
                    fat16.mkdir(path, [], patch.attrib, \
                            creationMicro=creationMicro, \
                            creationTime=creationTime, \
                            creationDate=creationDate, \
                            accessDate=accessDate, \
                            updateTime=updateTime, \
                            updateDate=updateDate )

                elif isinstance(patch, FAT_PATCH):
                    if len(patch.new_value) != len(patch.old_value):
                        raise Exception("Different length of old data and new data")
                    old_data = fat16.readFile(path)
                    if old_data[patch.offset:patch.offset + len(patch.old_value)] != patch.old_value:
                        raise Exception("Old data is not what we expected")
                    new_data  = old_data[:patch.offset]
                    new_data += patch.new_value
                    new_data += old_data[patch.offset + len(patch.new_value):]
                    print("Patching %s -> %s" % (patch.old_value.encode('hex'), patch.new_value.encode('hex')))
                    fat16.writeFile(path, new_data)
                elif isinstance(patch, FAT_FIX_JAD):
                    dir_path, fname = self.splitDirNameFname(path)
                    if fname[-4:] not in ['.jar', '.jad']:
                        raise Exception("Need a jar file name")
                    jadName = path[:-4] + '.jad'
                    jarName = path[:-4] + '.jar'
                    jar = fat16.getFileObj(jarName)
                    jad = fat16.getFileObj(jadName)
                    jarSize = jar.fileSize
                    jadData = jad.rawData
                    LABEL = 'MIDlet-Jar-Size: '
                    labelPos = jadData.find(LABEL)
                    if -1 == labelPos:
                        jadData += LABEL + str(jarSize) + '\n'
                    else:
                        endPos = jadData.find('\n', labelPos)
                        jadData = jadData[:labelPos] + LABEL + str(jarSize) + jadData[endPos:]
                    fat16.writeFile(jadName, jadData)
                elif isinstance(patch, FAT_SET_ATTRIB):
                    fat16.setAttributes(path, patch.new_attrib)
                elif isinstance(patch, FAT_MAKE_LINK_TO_FILE):
                    fat16.createLinkToFile(path, patch.dst, patch.prefixData, patch.attrib)
                elif isinstance(patch, FAT_MAKE_LINK_TO_DIR):
                    fat16.createLinkToDir(path, patch.dst, patch.attrib)
                else:
                    raise Exception("Unknown patch type %s" % repr(patch))


