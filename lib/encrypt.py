from Crypto.Cipher import AES
import logging
from . import constants

logger = logging.getLogger("Encryption")


def encrypt(flash_info: constants.FlashInfo, data_binary=None):

    if data_binary:
        logger.debug("Encrypting binary data")
        cipher = AES.new(flash_info.key, AES.MODE_CBC, flash_info.iv)
        cryptedContent = cipher.encrypt(data_binary)

        return cryptedContent
