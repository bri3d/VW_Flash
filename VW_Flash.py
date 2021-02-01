import sys, getopt
import logging
import argparse
import time

import lib.lzssHelper as lzss
import lib.checksum as checksum
import lib.encrypt as encrypt
import lib.constants as constants
import lib.flasher as flasher

#udsoncan.setup_logging(path.join(path.dirname(path.abspath(__file__)), 'logging.conf'))
#logger = logging.getLogger("VWFlash")
#logger.info("Started with configuration: " + str(block_files))


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
parser = argparse.ArgumentParser(description='VW_Flash CLI', 
    epilog="The MAIN CLI interface for using the tools herein")
parser.add_argument('--action', help="The action you want to take", 
    choices=['checksum', 'checksum_fix', 'lzss', 'encrypt', 'prepare', 'flash_bin', 'flash_prepared'], required=True)
parser.add_argument('--infile',help="the absolute path of an inputfile", action="append")
parser.add_argument('--outfile',help="the absolutepath of a file to output", action="store_true")
parser.add_argument('--block', type=str, help="The block name or number (defaults to CAL/5)", action="append")
parser.add_argument('--simos12', help="specify simos12, available for checksumming", action='store_true')

args = parser.parse_args()

def read_from_file(infile = None):
    f = open(infile, "rb")
    return f.read()

def write_to_file(outfile = None, data_binary = None):
    if outfile and data_binary:
        with open(outfile, 'wb') as fullDataFile:
            fullDataFile.write(data_binary)

if len(args.block) != len(args.infile):
    cliLogger.critical("You must specify a block for every infile")
    exit()

if args.block:
    blocks = [int(constants.block_to_number(block)) for block in args.block]

if args.infile:
    blocks_infile = dict(zip(blocks, args.infile))

else:
    print("No input file specified")
    exit()


def prepareBlocks():
    blocks_binary = {}
    timestr = time.strftime("%Y%m%d-%H%M%S")

    for block in blocks_infile:
        cliLogger.critical("Preparing " + blocks_infile[block] + " for flashing as block " + str(block))

        correctedFile = checksum.fix(simos12 = args.simos12, data_binary = read_from_file(blocks_infile[block]), blocknum = block, loglevel = logging.DEBUG)
    
        if correctedFile == constants.ChecksumState.FAILED_ACTION:
            logging.info("Failure to checksum and/or save file")
            continue
    
        tmpfile = '/tmp/' + timestr + "-prepare.checksummed_block" + str(block)
        write_to_file(outfile = tmpfile, data_binary = correctedFile)
    
        lzss.main(inputfile = tmpfile, outputfile = tmpfile + ".compressed")
        tmpfile = tmpfile + ".compressed"
    
        compressed_binary = read_from_file(tmpfile)
    
        if args.outfile:
            outfile = blocks_infile[block] + ".flashable_block" + str(block)
            cliLogger.critical("Writing encrypted block to: " + outfile)
            write_to_file(outfile = outfile, data_binary = encrypt.encrypt(data_binary = compressed_binary, loglevel = logging.DEBUG))

        else:
            cliLogger.critical("No outfile specified")
            blocks_binary[block] = encrypt.encrypt(data_binary = compressed_binary, loglevel = logging.DEBUG)

    return blocks_binary


#if statements for the various cli actions
if args.action == "checksum":

    for block in blocks_infile:
        cliLogger.critical("Checksumming: " + blocks_infile[block])

        result = checksum.validate(simos12 = args.simos12, data_binary = read_from_file(blocks_infile[block]), blocknum = block, loglevel = logging.DEBUG)

        if result == constants.ChecksumState.VALID_CHECKSUM:
            cliLogger.critical("Checksum on file was valid")
        elif result == constants.ChecksumState.INVALID_CHECKSUM:
            cliLogger.critical("Checksum on file was invalid")

if args.action == "checksum_fix":

    for block in blocks_infile:
        cliLogger.critical("Fixing Checksum for: " + blocks_infile[block])


        result = checksum.fix(simos12 = args.simos12, data_binary = read_from_file(blocks_infile[block]), blocknum = block, loglevel = logging.DEBUG)
        
        if result == constants.ChecksumState.FAILED_ACTION:
            cliLogger.critical("Checksum correction failed")
        
        if args.outfile:
            outfile = blocks_infile[block] + ".checksummed_block" + str(block)
            cliLogger.critical("Checksum correction successful, writing to: " + outfile)
            write_to_file(outfile = outfile, data_binary = result)
        else:
            cliLogger.critical("Checksum correction successful, but output not specified")

            


elif args.action == "lzss":

    for block in blocks_infile:
        
        if args.outfile:
            lzss.main(inputfile = blocks_infile[block], outputfile = blocks_infile[block] + ".compressed")
        else:
            cliLogger.critical("No outfile specified, skipping")



elif args.action == "encrypt":

    for block in blocks_infile:
        if args.outfile:
            outfile = blocks_infile[block] + ".flashable_block" + str(block)
            cliLogger.critical("Writing encrypted file to: " + outfile)
            write_to_file(outfile = outfile, data_binary = encrypt.encrypt(data_binary = read_from_file(blocks_infile[block]), loglevel = logging.DEBUG))
        else:
            cliLogger.critical("No outfile specified, skipping")


elif args.action == 'prepare':
    prepareBlocks()

elif args.action == 'flash_bin':
    blocks_binary = prepareBlocks()
    flasher.flash_blocks(blocks_binary)

elif args.action == 'flash_prepared':
    blocks_binary = {}
    for block in blocks_infile:
        blocks_binary[block] = read_from_file(blocks_infile[block])

    flasher.flash_blocks(blocks_binary)
