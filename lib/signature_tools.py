import logging
from Crypto.PublicKey import RSA
from pathlib import Path
from Crypto.Signature.pkcs1_15 import PKCS115_SigScheme
from Crypto.Hash import SHA256
from . import constants as constants
from .constants import FullBinData

logger = logging.getLogger("VWFlash")

VW_Flash_key = constants.internal_path("data", "VW_Flash.key")
VW_Flash_pub = constants.internal_path("data", "VW_Flash.pub")


#Build the metadata... basically just make sure the boxcode and the notes aren't too long
def build_metadata(boxcode = "", notes = ""):
    metadata = b'METADATA:' + boxcode[0:15].ljust(15,' ').encode("utf-8") + notes[0:70].ljust(70, ' ').encode("utf-8")
    return metadata

#sign binary data using a private key path
def sign_datablock(bin_file, private_key_path):
    with open(private_key_path, 'rb') as private_key_file:
        private_key = private_key_file.read()

    the_hash = SHA256.new(bin_file)
    pkcs115 = PKCS115_SigScheme(RSA.import_key(private_key))
    return pkcs115.sign(the_hash)    

#sign a bin... this will append metadata to a bin, and sign it (optionally twice), then return it
def sign_bin(bin_file, secondary_key_path = None, boxcode = "", notes = ""):
    metadata = build_metadata(boxcode = boxcode, notes = notes)
    bin_file += metadata
    
    signature1 = sign_datablock(bin_file, VW_Flash_key)

    if secondary_key_path:
        signature2 = sign_datablock(bin_file, secondary_key_path)
    else:
        signature2 = signature1
    
    signed_file = bin_file + signature1 + signature2

    return signed_file

#Verify a bin
def verify_bin(bin_file, signature, public_key_path):
    with open(public_key_path, 'rb') as public_key_file:
        public_key = public_key_file.read()


    the_hash = SHA256.new(bin_file)
    pkcs115 = PKCS115_SigScheme(RSA.import_key(public_key))

    try:
        verified = pkcs115.verify(the_hash, signature)
        return True
    except:
        return False

#write_bytes function... used to replace write_bytes throughout the code so it can be handled in a more
#centralized way
def write_bytes(outfile, binary_data, signed = False, secondary_key_path = None, boxcode = "", notes = ""):
    #Default, just write out to the file_path as bytes:
    if signed:
        binary_data = sign_bin(bin_file = binary_data, secondary_key_path = secondary_key_path, boxcode = boxcode, notes = notes)

    Path(outfile).write_bytes(binary_data)


#read_bytes function... used to replace read_bytes throughout the code so it can be handled in a more
#centralized way
def check_signature_data(bin_data, secondary_key_path = None):

    valid_signature_one = False
    valid_signature_two = False
    metadata = None

    #Check if there's metadata and signature(s) at the end of the file:
    sig_block = bin_data[-350:]
    if sig_block[0:9] == b'METADATA:':
        logger.info("Found signature block in bin file, validating")
        #Print out the metadata that's included in the file
        metadata = str(sig_block[0:-256])

        logger.info(str(sig_block[0:-256]))

        #Pull the signatures out
        signature1 = sig_block[-256:-128]
        signature2 = sig_block[-128:]

        #Validate the first signature using the VW_Flash public key
        if verify_bin(bin_data[0:-256], signature1, VW_Flash_pub):
            logger.info("First signature validated")
            valid_signature_one = True
        else:
            logger.critical("First signature failed!  File has been modified!")

        #if the signatures are the same, there's no point checking the second one, just continue on
        if signature1 == signature2:
            logger.info("No secondary signature found")

        elif secondary_key_path:
            if verify_bin(bin_data[0:-256], signature2, secondary_key_path):
                logger.info("Second signature validated")
                valid_signature_two = True
            else:
                logger.critical("Second signature failed!")

        else:
            logger.info("File contains additional signature, but no public key arg provided")

        #Pull the signature block off the end of the bin file so we can process it by itself
        bin_data = bin_data[0:-350]


    return FullBinData({"full_bin": bin_data}, metadata, valid_signature_one, valid_signature_two)

