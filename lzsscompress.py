import argparse

import lib.lzssHelper as lzss


parser = argparse.ArgumentParser(description='Script for using the lzss C program', epilog="For example, --infile INPUTFILE --outfile OUTPUTFILE")
parser.add_argument('--infile',help="the absolute path of the input file to compress")
parser.add_argument('--outfile',help="the absolutepath of the file to output (by default, .compressed will be appended)")

args = parser.parse_args()

if args.infile:
    inputFile = args.infile

if args.outfile:
    outputFile = args.outfile
else:
    outputFile = args.infile + ".compressed"


lzss.main(inputfile = inputFile, outputfile = outputFile)


