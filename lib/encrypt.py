from Crypto.Cipher import AES
import logging
from lib import constants

rootLogger = logging.getLogger()

def encrypt(data_binary = None, loglevel=logging.INFO):

   if data_binary:
      rootLogger.debug("Encrypting binary data")
      cipher = AES.new(constants.s18_key, AES.MODE_CBC, constants.s18_iv)
      cryptedContent = cipher.encrypt(data_binary)
      
      return cryptedContent
 

