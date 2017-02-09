
import sys

from distutils.core import setup
try:
    import py2exe
except:
    pass
from phosher import *
import scipy

packagesNames = [
        'phosher',
        'phosher\\asha',
        'phosher\\bb5',
        'phosher\\dct4',
        'phosher\\contentParsers',
        'phosher\\fat16',
        'phosher\\crypto',
        'phosher\\general' ]
packagesDirs = {
        'phosher' : '.',
        'phosher\\asha' : "asha",
        'phosher\\bb5' : "bb5",
        'phosher\\dct4' : "dct4",
        'phosher\\contentParsers' : "contentParsers",
        'phosher\\fat16' : "fat16",
        'phosher\\crypto' : "crypto",
        'phosher\\general' : "general" }
dll_excludes = []
includes = []
excludes = []
setup(
        options = {
            "py2exe": {
                "compressed": 2,
                "optimize": 2,
                "packages": ["phosher"],
                "dll_excludes": dll_excludes,
                "bundle_files": 2,
                "dist_dir": "dist",
                "xref": False,
                "skip_archive": False,
                "ascii": False,
                "custom_boot_script": '',
                }
        },
        name = "phosher",
        version = "1.0",
        description = "Kosher phones creating and researching scripts",
        author = "Assaf Nativ",
        author_email = "Nativ.Assaf@gmail.com",
        packages = packagesNames,
        package_dir = packagesDirs,
        data_files = [('Lib\\site-packages', ('phosher.pth',))],
        console=["nokiaPhosher.py"]
        )
