import sys, getopt
import logging
import argparse

import lib.lzssHelper as lzss
import lib.checksum as checksum
import lib.encrypt as encrypt
import lib.constants as constants

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
parser.add_argument('--action', help="The action you want to take", choices=['checksum', 'lzss', 'encrypt', 'prepare'], required=True)
parser.add_argument('--infile',help="the absolute path of an inputfile")
parser.add_argument('--outfile',help="the absolutepath of a file to output")
parser.add_argument('--block', type=str, help="The block name or number (required for checksumming, defaults to CAL/5)")
parser.add_argument('--simos12', help="specify simos12, available for checksumming", action='store_true')

args = parser.parse_args()

#Default to block 5 (the cal block), and override if specified
block = 5

if args.block:
    block = constants.block_to_number(args.block)


infile = ''
outfile = ''

#outfile doesn't need to be specified, but if it was, we'll use it
if args.outfile:
    outfile = args.outfile

#if statements for the various cli actions
if args.action == "checksum":

    #Print an error if no input file was specified
    if args.infile is None:
        cliLogger.critical("Must specify an input file to checksum")
        exit()

    else:
        result = checksum.main(simos12 = args.simos12, inputfile = args.infile, outputfile = outfile, blocknum = block, loglevel = logging.DEBUG)

        cliLogger.critical(str(result))


elif args.action == "lzss":

    if args.infile is None:
        cliLogger.critical("Must specify an input file to lzss")
        exit()
    else:
        if args.outfile:
            lzss.main(inputfile = args.infile, outputfile = args.outfile)
        else:
            lzss.main(inputfile = args.infile, outputfile = args.infile + ".compressed")



elif args.action == "encrypt":

    if args.infile is None:
        cliLogger("Must specify an input file to encrypt")
    else:
        if args.outfile:
            encrypt.main(inputfile = args.infile, outputfile = args.outfile, loglevel = logging.DEBUG)
        else:
            encrypt.main(inputfile = args.infile, outputfile = args.infile + ".flashable", loglevel = logging.DEBUG)


elif args.action == 'prepare':
    binfile = ''

    if args.infile:
        binfile = args.infile
    else:
        cliLogger.critical("You must specify a file to prepare for flashing")
        exit()

    result = checksum.main(simos12 = args.simos12, inputfile = binfile, outputfile = binfile + ".checksummed_block" + str(block), blocknum = block, loglevel = logging.DEBUG)

    if result is False:
        logging.info("Failure to checksum and/or save file")
        exit()
    else:
        binfile = binfile + ".checksummed_block" + str(block)

    lzss.main(inputfile = binfile, outputfile = binfile + ".compressed")
    binfile = binfile + ".compressed"
    encrypt.main(inputfile = binfile, outputfile = binfile + ".flashable", loglevel = logging.DEBUG)



