
import phosher.contentParsers as contentParsers
from phosher.contentParsers import *
import sys

PARSERS = [parser for parser in contentParsers.__all__ if '__' not in parser]

def printSyntaxAndExit():
    print "Please choose parser from the list:"
    for parser in PARSERS:
        print "\t%s" % parser
    sys.exit(1)

def main():
    if len(sys.argv) < 2:
        printSyntaxAndExit()
    parserToUse = sys.argv[1]
    if parserToUse not in PARSERS:
        printSyntaxAndExit()
    else:
        parser = globals()[parserToUse]
        sys.argv = sys.argv[1:]
        parser.main()

if __name__ == "__main__":
    main()
