
# Fuck this shit! JAR is to fucked up!
# Just use:
# jar cvfm wocl.jar MANIFEST.MF -C wocl .
#

from subprocess import *
import zipfile
import time
from glob import glob
import os

if 'nt' == os.name:
    ZIP7_PATH = r'"c:\Program Files\7-Zip\7z.exe"'
    ZIP_PATH  = r'c:\tools\zip\zip.exe'
else:
    ZIP7_PATH = r'7z'
    ZIP_PATH  = r'zip'

def parseManifest(fname):
    lines = file(fname, 'r').readlines()
    lines = [l.strip() for l in lines]
    lines = [_f for _f in lines if _f]
    manifest = dict([tuple(x.split(':')) for x in lines])
    return manifest

def createJar(src_dir, out_file, method='pyzip', files_list=None):
    if os.path.isfile(out_file):
        os.remove(out_file)
    if 'pyzip' == method and isinstance(out_file, str):
        out_file = zipfile.ZipFile(out_file, 'w')
        needToClose = True
    else:
        needToClose = False
    if None == files_list:
        manifest_full_path = src_dir + os.sep + 'META-INF' + os.sep + 'MANIFEST.MF'
        jarAddFile(out_file, 'META-INF',         compress=True, method=method, isFolder=True, ver=10)
        jarAddFile(out_file, manifest_full_path, compress=True, method=method, isFolder=False, ver=10, inter="META-INF/")
        manifest = parseManifest(src_dir + os.sep + 'META-INF' + os.sep + 'MANIFEST.MF')
        midlet1 = manifest['MIDlet-1']
        classname = midlet1.split(', ')[2]
        classname = classname.replace('.', '/')
        classname += '.class'
        jarAddFiles([src_dir + os.sep + classname], out_file, method=method)
        files_list = [fn for fn in glob(src_dir + os.sep + '*') if 'META-INF' not in fn]
        files_list = [fn for fn in files_list if not fn.endswith(classname)]
        files_list = [fn for fn in files_list if '.' != fn and '..' != fn]
        jarAddFiles(files_list, out_file, method=method)
    else:
        for fname in files_list:
            is_folder = (fname[-1] == '/')
            inter = os.path.dirname(fname)
            if not is_folder:
                full_path = src_dir + os.sep + fname.replace('/', os.sep)
                jarAddFile(out_file, full_path, in_zip_name=fname, compress=True, method=method, isFolder=is_folder, ver=10)
            else:
                jarAddFile(out_file, '', in_zip_name=fname, compress=True, method=method, isFolder=is_folder, ver=10)
    if needToClose:
        out_file.close()
        #return out_file

def jarAddFiles(files_list, zip_file, compress=True, inter=None, method='pyzip', ver=10):
    if None == inter:
        inter = ""
    if 'pyzip' != method:
        for fname in files_list:
            if fname.endswith('~'):
                continue
            jarAddFile(zip_file, fname, compress, method=method)
    else:
        for fname in files_list:
            if fname.endswith('~'):
                continue
            base = os.path.basename(fname)
            if os.path.isdir(fname):
                new_files_list = [fn for fn in glob(fname + os.sep + '*') if '.' != fn and '..' != fn]
                jarAddFile(zip_file, fname, compress=False, method=method, inter=inter, isFolder=True, ver=ver)
                jarAddFiles(new_files_list, zip_file, compress=compress, inter=inter + base + '/', ver=ver)
            else:
                jarAddFile(zip_file, fname, compress=compress, method=method, inter=inter, isFolder=False, ver=ver)

def jarAddFile(zip_file, fname, in_zip_name=None, compress=True, method='pyzip', inter=None, isFolder=False, ver=10):
    if 'pyzip' == method:
        if None == inter:
            inter = ""
        if None == in_zip_name:
            base = os.path.basename(fname)
            if isFolder:
                base += '/'
            in_zip_name = str(inter + base)
        else:
            base = in_zip_name
        info = zipfile.ZipInfo(in_zip_name)
        info.date_time = (2013, 1, 24, 10, 43, 46)
        info.comment = ''
        if 'META-INF/' == base:
            info.extra = '\xfe\xca\x00\x00'
        else:
            info.extra = ''
        if compress:
            info.compress_type = zipfile.ZIP_DEFLATED
        else:
            info.compress_type = zipfile.ZIP_STORED
        info.create_system = 3
        info.create_version = 20
        info.extract_version = ver
        info.flag_bits = 2048
        info.volume = 0
        info.internal_attr = 0
        if isFolder:
            info.file_size = 0
            info.compress_size = 0
            info.CRC = 0
            info.external_attr = 0x41ed0010
            info.header_offset  = sum([f.compress_size for f in zip_file.filelist])
            info.header_offset += sum([len(f.FileHeader()) for f in zip_file.filelist])
            zip_file.filelist.append(info)
            zip_file._didModify = True
            zip_file.fp.write(info.FileHeader())
            #zip_file.writestr(info, '')
        else:
            info.external_attr = 0x81a40000
            zip_file.writestr(info, file(fname, 'rb').read())
    elif '7zip' == method:
        if compress:
            method = '3'
        else:
            method = '0'
        cmd = '%s a -tzip -scsUTF-8 -mcu -mx%s %s %s >nul' % (ZIP7_PATH, method, zip_file, fname)
        print(("Executing: %s" % cmd))
        os.system(cmd)
    elif 'zip' == method:
        if compress:
            method = ''
        else:
            method = '-0'
        dirname = os.path.dirname(fname)
        basename = os.path.basename(fname)
        cmd = '%s %s -r -UN=UTF8 %s %s' % (ZIP_PATH, method, zip_file, basename)
        print(("Executing: %s" % cmd))
        Popen(cmd, shell=True, cwd=dirname).communicate()
    else:
        raise Exception("Unknown method")

def compareZips(z1, z2):
    z1 = zipfile.ZipFile(z1)
    z2 = zipfile.ZipFile(z2)
    if len(z1.filelist) != len(z2.filelist):
        print("Not same number of files!")
        return
    for i in range(len(z1.filelist)):
        f1 = z1.filelist[i]
        f2 = z2.filelist[i]
        if f1.filename != f2.filename:
            print(('Name mismatch', f1.filename, f2.filename))
            continue
        if f1.create_system != f2.create_system:
            print(('Create system mismatch', f1.filename))
        if f1.file_size != f2.file_size:
            print(('File size mismatch', f1.filename))
        if f1.compress_size != f2.compress_size:
            print('Compress size mismatch', f1.filename)
        if f1.CRC != f2.CRC:
            print('CRC mismatch', f1.filename)
        if f1.external_attr != f2.external_attr:
            print('External attr mismatch', f1.filename)
        if f1.flag_bits != f2.flag_bits:
            print('Flag bits mismatch', f1.filename)
