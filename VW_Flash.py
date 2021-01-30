import sys, getopt
import logging
from Crypto.Cipher import AES
import binascii
import argparse

import lib.lzssHelper as lzss
import lib.checksum as checksum
import lib.encrypt as encrypt


parser = argparse.ArgumentParser(description='VW_Flash CLI', epilog="The MAIN CLI interface for using the tools herein")
parser.add_argument('--action', help="The action you want to take", choices=['checksum', 'lzss', 'encrypt'], required=True)
parser.add_argument('--infile',help="the absolute path of an inputfile")
parser.add_argument('--outfile',help="the absolutepath of a file to output")
parser.add_argument('--block', help="The block number (required for checksumming")
parser.add_argument('--simos12', help="specify simos12, available for checksumming", action='store_true')

args = parser.parse_args()

if args.action == "checksum":
    block = 5
    if args.block:
        block = int(args.block)

    if args.infile is None:
        print("Must specify an input file to checksum")

    else:
        if args.outfile is None:
            result = checksum.main(simos12 = args.simos12, inputfile = args.infile, outputfile = '', blocknum = block, loglevel = logging.DEBUG)
        else:
            result = checksum.main(simos12 = args.simos12, inputfile = args.infile, outputfile = args.outfile, blocknum = block, loglevel = logging.DEBUG)


elif args.action == "lzss":

    if args.infile is None:
        print("Must specify an input file to lzss")
    else:
        if args.outfile:
            lzss.main(inputfile = args.infile, outputfile = args.outfile)
        else:
            lzss.main(inputfile = args.infile, outputfile = args.outfile + ".compressed")



elif args.action == "encrypt":

    if args.infile is None:
        print("Must specify an input file to encrypt")
    else:
        if args.outfile:
            encrypt.main(inputfile = args.infile, outputfile = args.outfile, loglevel = logging.DEBUG)
        else:
            encrypt.main(inputfile = args.infile, outputfile = args.infile + ".flashable", loglevel = logging.DEBUG)


