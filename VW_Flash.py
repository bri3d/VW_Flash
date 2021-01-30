import sys, getopt
import logging
import argparse

import lib.lzssHelper as lzss
import lib.checksum as checksum
import lib.encrypt as encrypt

#Set up logging (instead of printing to stdout)
cliLogger = logging.getLogger()

#Set it to debug by default
cliLogger.setLevel(logging.DEBUG)

#Set up a logging handler to print to stdout
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)

#Set the logging format, and add the handler to the logger
formatter = logging.Formatter('%(asctime)s - %(message)s')
handler.setFormatter(formatter)
cliLogger.addHandler(handler)


#Set up the argument/parser with run options
parser = argparse.ArgumentParser(description='VW_Flash CLI', epilog="The MAIN CLI interface for using the tools herein")
parser.add_argument('--action', help="The action you want to take", choices=['checksum', 'lzss', 'encrypt'], required=True)
parser.add_argument('--infile',help="the absolute path of an inputfile")
parser.add_argument('--outfile',help="the absolutepath of a file to output")
parser.add_argument('--block', help="The block number (required for checksumming, defaults to CAL/5)")
parser.add_argument('--simos12', help="specify simos12, available for checksumming", action='store_true')

args = parser.parse_args()

infile = ''
outfile = ''

#outfile doesn't need to be specified, but if it was, we'll use it
if args.outfile:
    outfile = args.outfile

#if statements for the various cli actions
if args.action == "checksum":

    #Default to block 5 (the cal block), and override if specified
    block = 5
    if args.block:
        block = int(args.block)

    #Print an error if no input file was specified
    if args.infile is None:
        print("Must specify an input file to checksum")
        exit()

    else:
        result = checksum.main(simos12 = args.simos12, inputfile = args.infile, outputfile = outfile, blocknum = block, loglevel = logging.DEBUG)


elif args.action == "lzss":

    if args.infile is None:
        print("Must specify an input file to lzss")
    else:
        if args.outfile:
            lzss.main(inputfile = args.infile, outputfile = args.outfile)
        else:
            lzss.main(inputfile = args.infile, outputfile = args.infile + ".compressed")



elif args.action == "encrypt":

    if args.infile is None:
        print("Must specify an input file to encrypt")
    else:
        if args.outfile:
            encrypt.main(inputfile = args.infile, outputfile = args.outfile, loglevel = logging.DEBUG)
        else:
            encrypt.main(inputfile = args.infile, outputfile = args.infile + ".flashable", loglevel = logging.DEBUG)


