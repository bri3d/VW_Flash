from Crypto.Cipher import AES
import logging
from . import constants

logger = logging.getLogger("Encryption")


def encrypt(data_binary=None):

    if data_binary:
        logger.debug("Encrypting binary data")
        cipher = AES.new(constants.s18_key, AES.MODE_CBC, constants.s18_iv)
        cryptedContent = cipher.encrypt(data_binary)

        return cryptedContent
