
import sys

from distutils.core import setup

packagesNames = [
        'phosher', 
        'phosher\\general',
        'phosher\\asha', 
        'phosher\\dct4', 
        'phosher\\crypto', 
        'phosher\\fat16',
        'phosher\\image',
        ]
packagesDirs = {
        'phosher' : '.', 
        'phosher\\general'  : 'general',
        'phosher\\asha'     : 'asha',
        'phosher\\dct4'     : 'dct4',
        'phosher\\crypto'   : 'crypto',
        'phosher\\fat16'    : 'fat16',
        'phosher\\image'    : 'image',
        }
setup(
        name = "phosher",
        version = "1.0",
        description = "Kosher phones creating and researching scripts",
        author = "Assaf Nativ",
        author_email = "Nativ.Assaf@gmail.com",
        packages = packagesNames,
        package_dir = packagesDirs,
        data_files = [('Lib\\site-packages', ('phosher.pth',))]
        )
