
import sys

from distutils.core import setup

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
