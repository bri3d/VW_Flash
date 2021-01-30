from Crypto.Cipher import AES
import logging
from lib import constants

rootLogger = logging.getLogger()

def main(inputfile = None, outputfile = None, loglevel=logging.INFO):

   if inputfile and outputfile:
      rootLogger.debug("Encrypting " + inputfile + " to " + outputfile)
      f = open(inputfile, "rb")
      dataBinary = f.read()    
      cipher = AES.new(constants.s18_key, AES.MODE_CBC, constants.s18_iv)
      cryptedContent = cipher.encrypt(dataBinary)
      with open(outputfile, 'wb') as fullDataFile:
         fullDataFile.write(cryptedContent)

      return True
   
