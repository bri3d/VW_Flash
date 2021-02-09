import sys
import logging
import argparse
import time
import base64

from . import lzssHelper as lzss
from . import checksum as simos_checksum
from . import encrypt as encrypt
from . import constants as constants
from . import simos_uds as simos_uds

#udsoncan.setup_logging(path.join(path.dirname(path.abspath(__file__)), 'logging.conf'))
#logger = logging.getLogger("VWFlash")
#logger.info("Started with configuration: " + str(block_files))


#Set up logging (instead of printing to stdout)
cliLogger = logging.getLogger("FlashUtils")

#Set it to debug by default
cliLogger.setLevel(logging.DEBUG)


def read_from_file(infile = None):
    f = open(infile, "rb")
    return f.read()

def write_to_file(outfile = None, data_binary = None):
    if outfile and data_binary:
        with open(outfile, 'wb') as fullDataFile:
            fullDataFile.write(data_binary)

def decodeBlocks(base64_blocks):
    blocks_infile = {}

    for filename in base64_blocks:
        base64_data = base64_blocks[filename]['base64_data']
        blocknum = base64_blocks[filename]['blocknum']

        blocks_infile[filename] = {'binary_data': base64.b64decode(str(base64_data)), 'blocknum': blocknum}

    return blocks_infile

def callback_function(message):
    cliLogger.critical(message)

def prepareBlocks(blocks_infile, callback = None):
    timestr = time.strftime("%Y%m%d-%H%M%S")

    for filename in blocks_infile:
        binary_data = blocks_infile[filename]['binary_data']
        blocknum = blocks_infile[filename]['blocknum']

        if callback:
            callback(flasher_step = 'PREPARING', flasher_status = "Preparing " + filename + " for flashing as block " + str(blocknum), flasher_progress = 20)

        cliLogger.critical("Preparing " + filename + " for flashing as block " + str(blocknum))

        if callback:
            callback(flasher_step = 'PREPARING', flasher_status = "Checksumming " + filename + " as block " + str(blocknum), flasher_progress = 40)

        correctedFile = simos_checksum.fix(data_binary = binary_data, blocknum = blocknum) if blocknum < 6 else binary_data
    
        if correctedFile == constants.ChecksumState.FAILED_ACTION:
            cliLogger.critical("Failure to checksum and/or save file")
            continue
        else:
            cliLogger.warning("File Checksum corrected")
    
        tmpfile = '/tmp/' + timestr + "-prepare.checksummed_block" + str(blocknum)
        write_to_file(outfile = tmpfile, data_binary = correctedFile)
 
        if callback:
            callback(flasher_step = 'PREPARING', flasher_status = "Compressing " + filename, flasher_progress = 60)

        lzss.main(inputfile = tmpfile, outputfile = tmpfile + ".compressed")
        tmpfile = tmpfile + ".compressed"
    
        compressed_binary = read_from_file(tmpfile) if blocknum < 6 else binary_data
 
        if callback:
            callback(flasher_step = 'PREPARING', flasher_status = "Encrypting " + filename, flasher_progress = 80)

        blocks_infile[filename]['binary_data'] = encrypt.encrypt(data_binary = compressed_binary)

    return blocks_infile

#if statements for the various cli actions
def checksum(blocks_infile):
    for filename in blocks_infile:
        binary_data = blocks_infile[filename]['binary_data']
        blocknum = blocks_infile[filename]['blocknum']

        cliLogger.critical("Checksumming: " + filename + " as block: " + str(blocknum))

        result = simos_checksum.validate(data_binary = binary_data, blocknum = blocknum)

        if result == constants.ChecksumState.VALID_CHECKSUM:
            cliLogger.critical("Checksum on file was valid")
        elif result == constants.ChecksumState.INVALID_CHECKSUM:
            cliLogger.critical("Checksum on file was invalid")

def checksum_fix(blocks_infile):
    for filename in blocks_infile:
        binary_data = blocks_infile[filename]['binary_data']
        blocknum = blocks_infile[filename]['blocknum']

      
        cliLogger.critical("Fixing Checksum for: " + filename + " as block: " + str(blocknum))


        result = simos_checksum.fix(data_binary = binary_data, blocknum = blocknum)
        
        if result == constants.ChecksumState.FAILED_ACTION:
            cliLogger.critical("Checksum correction failed")
        
        cliLogger.critical("Checksum correction successful")
        blocks_infile[filename]['binary_data'] = result

    return blocks_infile

            


def lzss_compress(blocks_infile, outfile = None):
    for filename in blocks_infile:
        
        if outfile:
            lzss.main(inputfile = filename, outputfile = filename + ".compressed")
        else:
            cliLogger.critical("No outfile specified, skipping")



def encrypt_blocks(blocks_infile):
    for filename in blocks_infile:
        binary_data = blocks_infile[filename]['binary_data']
        blocknum = blocks_infile[filename]['blocknum']
 

        blocks_infile[filename]['binary_data'] = encrypt.encrypt(data_binary = binary_data)

    return blocks_infile


def flash_bin(blocks_infile, callback = None):

    blocks_infile = prepareBlocks(blocks_infile, callback)
    simos_uds.flash_blocks(block_files = blocks_infile, callback = callback)

def flash_base64(base64_infile, callback = None):
    if callback:
        callback(flasher_step = 'DECODING', flasher_status = "Preparing to Base64 decode the block(s)", flasher_progress = 0)
    blocks_infile = decodeBlocks(base64_infile)
    flash_bin(blocks_infile, callback)

def flash_prepared(blocks_infile):
    simos_uds.flash_blocks(blocks_infile)
