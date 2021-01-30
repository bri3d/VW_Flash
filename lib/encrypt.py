import sys, getopt
from Crypto.Cipher import AES
import binascii
import logging

rootLogger = logging.getLogger()

def main(inputfile = None, outputfile = None, loglevel=logging.INFO):

   if inputfile and outputfile:
      rootLogger.debug("Encrypting " + inputfile + " to " + outputfile)
      key = binascii.unhexlify('98D31202E48E3854F2CA561545BA6F2F')
      iv = binascii.unhexlify('E7861278C508532798BCA4FE451D20D1')
      f = open(inputfile, "rb")
      dataBinary = f.read()    
      cipher = AES.new(key, AES.MODE_CBC, iv)
      cryptedContent = cipher.encrypt(dataBinary)
      with open(outputfile, 'wb') as fullDataFile:
         fullDataFile.write(cryptedContent)

      return True
   
