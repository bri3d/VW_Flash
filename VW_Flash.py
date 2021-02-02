import sys
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

block_number_help = []
for name, number in constants.block_name_to_int.items():
    block_number_help.append(name)
    block_number_help.append(str(number))


#Set up the argument/parser with run options
parser = argparse.ArgumentParser(description='VW_Flash CLI', 
    epilog="The MAIN CLI interface for using the tools herein")
parser.add_argument('--action', help="The action you want to take", 
    choices=['checksum', 'checksum_fix', 'lzss', 'encrypt', 'prepare', 'flash_bin', 'flash_prepared'], required=True)
parser.add_argument('--infile',help="the absolute path of an inputfile", action="append")
parser.add_argument('--outfile',help="the absolutepath of a file to output", action="store_true")
parser.add_argument('--block', type=str, help="The block name or number", 
    choices=block_number_help, action="append", required=True)
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

#convert --blocks on the command line into a list of ints
if args.block:
    blocks = [int(constants.block_to_number(block)) for block in args.block]

#build the dict that's used to proces the blocks
#  Everything is structured based on the following format:
#  {'infile1': {'blocknum': num, 'binary_data': binary},
#     'infile2: {'blocknum': num2, 'binary_data': binary2}
#  }
if args.infile:
    blocks_infile = {}
    for i in range(0, len(args.infile)):
        blocks_infile[args.infile[i]] = {'blocknum': blocks[i], 'binary_data': read_from_file(args.infile[i])}

else:
    print("No input file specified")
    exit()



def prepareBlocks():
    blocks_binary = {}
    timestr = time.strftime("%Y%m%d-%H%M%S")

    for filename in blocks_infile:
        binary_data = blocks_infile[filename]['binary_data']
        blocknum = blocks_infile[filename]['blocknum']

        cliLogger.critical("Preparing " + filename + " for flashing as block " + str(blocknum))

        correctedFile = checksum.fix(simos12 = args.simos12, data_binary = binary_data, blocknum = blocknum, loglevel = logging.DEBUG) if blocknum < 6 else binary_data
    
        if correctedFile == constants.ChecksumState.FAILED_ACTION:
            logging.info("Failure to checksum and/or save file")
            continue
    
        tmpfile = '/tmp/' + timestr + "-prepare.checksummed_block" + str(blocknum)
        write_to_file(outfile = tmpfile, data_binary = correctedFile)
    
        lzss.main(inputfile = tmpfile, outputfile = tmpfile + ".compressed")
        tmpfile = tmpfile + ".compressed"
    
        compressed_binary = read_from_file(tmpfile) if blocknum < 6 else binary_data
    
        if args.outfile:
            outfile = filename + ".flashable_block" + str(blocknum)
            cliLogger.critical("Writing encrypted block to: " + outfile)
            write_to_file(outfile = outfile, data_binary = encrypt.encrypt(data_binary = compressed_binary, loglevel = logging.DEBUG))

        else:
            cliLogger.critical("No outfile specified")
            blocks_infile[filename]['binary_data'] = encrypt.encrypt(data_binary = compressed_binary, loglevel = logging.DEBUG)

    return blocks_binary


#if statements for the various cli actions
if args.action == "checksum":

    for filename in blocks_infile:
        binary_data = blocks_infile[filename]['binary_data']
        blocknum = blocks_infile[filename]['blocknum']

        cliLogger.critical("Checksumming: " + filename + " as block: " + blocknum)

        result = checksum.validate(simos12 = args.simos12, data_binary = binary_data, blocknum = blocknum, loglevel = logging.DEBUG)

        if result == constants.ChecksumState.VALID_CHECKSUM:
            cliLogger.critical("Checksum on file was valid")
        elif result == constants.ChecksumState.INVALID_CHECKSUM:
            cliLogger.critical("Checksum on file was invalid")

if args.action == "checksum_fix":

    for filename in blocks_infile:
        binary_data = blocks_infile[filename]['binary_data']
        blocknum = blocks_infile[filename]['blocknum']

      
        cliLogger.critical("Fixing Checksum for: " + filename + " as block: " + blocknum)


        result = checksum.fix(simos12 = args.simos12, data_binary = binary_data, blocknum = blocknum, loglevel = logging.DEBUG)
        
        if result == constants.ChecksumState.FAILED_ACTION:
            cliLogger.critical("Checksum correction failed")
        
        if args.outfile:
            outfile = filename + ".checksummed_block" + str(blocknum)
            cliLogger.critical("Checksum correction successful, writing to: " + outfile)
            write_to_file(outfile = outfile, data_binary = result)
        else:
            cliLogger.critical("Checksum correction successful, but output not specified")
            blocks_infile[filename]['binary_data'] = result

            


elif args.action == "lzss":

    for filename in blocks_infile:
        
        if args.outfile:
            lzss.main(inputfile = filename, outputfile = filename + ".compressed")
        else:
            cliLogger.critical("No outfile specified, skipping")



elif args.action == "encrypt":

    for filename in blocks_infile:
        binary_data = blocks_infile[filename]['binary_data']
        blocknum = blocks_infile[filename]['blocknum']
 

        if args.outfile:
            outfile = filename + ".flashable_block" + str(blocknum)
            cliLogger.critical("Writing encrypted file to: " + outfile)
            write_to_file(outfile = outfile, data_binary = encrypt.encrypt(data_binary = binary_data, loglevel = logging.DEBUG))
        else:
            cliLogger.critical("No outfile specified, skipping")


elif args.action == 'prepare':
    prepareBlocks()

elif args.action == 'flash_bin':
    cliLogger.critical("Executing flash_bin with the following blocks:\n" + 
      "\n".join([' : '.join([
           filename, 
           str(blocks_infile[filename]['blocknum']), 
           str(blocks_infile[filename]['binary_data'][constants.software_version_location[blocks_infile[filename]['blocknum']][0]:constants.software_version_location[blocks_infile[filename]['blocknum']][1]])]) for filename in blocks_infile]))


    prepareBlocks()
    flasher.flash_blocks(blocks_infile)

elif args.action == 'flash_prepared':

    flasher.flash_blocks(blocks_infile)
