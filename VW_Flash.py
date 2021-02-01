import sys, getopt
import logging
import argparse
import time

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
parser.add_argument('--action', help="The action you want to take", choices=['checksum', 'checksum_fix', 'lzss', 'encrypt', 'prepare'], required=True)
parser.add_argument('--infile',help="the absolute path of an inputfile")
parser.add_argument('--outfile',help="the absolutepath of a file to output")
parser.add_argument('--block', type=str, help="The block name or number (required for checksumming, defaults to CAL/5)")
parser.add_argument('--simos12', help="specify simos12, available for checksumming", action='store_true')

args = parser.parse_args()

def read_from_file(infile = None):
    f = open(infile, "rb")
    return f.read()

def write_to_file(outfile = None, data_binary = None):
    if outfile and data_binary:
        with open(outfile, 'wb') as fullDataFile:
            fullDataFile.write(data_binary)



#Default to block 5 (the cal block), and override if specified
block = 5

if args.block:
    block = constants.block_to_number(args.block)

if args.infile:
    infile_binary = read_from_file(infile = args.infile)

else:
   infile_binary = None

outfile = None

#outfile doesn't need to be specified, but if it was, we'll use it
if args.outfile:
    outfile = args.outfile

#if statements for the various cli actions
if args.action == "checksum":

    #Print an error if no input file was specified
    if infile_binary is None:
        cliLogger.critical("Must specify an input file to checksum")
        exit()

    else:
        result = checksum.validate(simos12 = args.simos12, data_binary = infile_binary, blocknum = block, loglevel = logging.DEBUG)

        if result == constants.ChecksumState.VALID_CHECKSUM:
            cliLogger.critical("Checksum on file was valid")
        elif result == constants.ChecksumState.INVALID_CHECKSUM:
            cliLogger.critical("Checksum on file was invalid")
        elif result == constants.ChecksumState.FIXED_CHECKSUM:
            cliLogger.critical("Checksum on file was fixed, wrote to: " + outfile)

if args.action == "checksum_fix":

    #Print an error if no input file was specified
    if infile is None:
        cliLogger.critical("Must specify an input file to checksum")
        exit()

    else:
        result = checksum.fix(simos12 = args.simos12, data_binary = infile_binary, blocknum = block, loglevel = logging.DEBUG)

        if result == constants.ChecksumState.FAILED_ACTION:
            cliLogger.critical("Checksum correction failed")
            exit()

        if outfile is not None:
            cliLogger.critical("Checksum correction successful, writing to: " + outfile)
            write_to_file(outfile = outfile, data_binary = result)
        else:
            cliLogger.critical("Checksum correction successful, writing to: " + args.infile + ".checksummed_block" + str(block))
            write_to_file(outfile = args.infile + ".checksummed_block" + str(block), data_binary = result)
        
            


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
            write_to_file(outfile = args.outfile, data_binary = encrypt.encrypt(data_binary = infile_binary, loglevel = logging.DEBUG))
        else:
            cliLogger.critical("No output file specified, writing to : " + args.infile + ".flashable")
            write_to_file(outfile = args.infile + ".flashable", data_binary = encrypt.encrypt(data_binary = infile_binary, loglevel = logging.DEBUG))


elif args.action == 'prepare':
    timestr = time.strftime("%Y%m%d-%H%M%S")

    binfile = ''

    if args.infile:
        binfile = args.infile
    else:
        cliLogger.critical("You must specify a file to prepare for flashing")
        exit()

    correctedFile = checksum.fix(simos12 = args.simos12, data_binary = infile_binary, blocknum = block, loglevel = logging.DEBUG)

    if correctedFile == constants.ChecksumState.FAILED_ACTION:
        logging.info("Failure to checksum and/or save file")
        exit()

    tmpfile = '/tmp/' + timestr + "-prepare.checksummed_block" + str(block)
    write_to_file(outfile = tmpfile, data_binary = correctedFile)

    lzss.main(inputfile = tmpfile, outputfile = tmpfile + ".compressed")
    tmpfile = tmpfile + ".compressed"

    compressed_binary = read_from_file(tmpfile)

    if args.outfile:
        write_to_file(outfile = args.outfile, data_binary = encrypt.encrypt(data_binary = compressed_binary, loglevel = logging.DEBUG))
    else:
        cliLogger.critical("No output file specified, writing to: " + args.infile + ".flashable")
        write_to_file(outfile = args.infile + ".flashable", data_binary = encrypt.encrypt(data_binary = compressed_binary, loglevel = logging.DEBUG))



