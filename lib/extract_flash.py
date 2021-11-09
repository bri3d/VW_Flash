import io
import zipfile
from frf import decryptfrf
import extractodx
from . import constants
from .modules import simos18, simos1810


def extract_flash_from_frf(
    frf_data: bytes, flash_info: constants.FlashInfo, is_dsg=False
):
    decrypted_frf = decryptfrf.decrypt_data(decryptfrf.read_key_material(), frf_data)
    zf = zipfile.ZipFile(io.BytesIO(decrypted_frf), "r")

    for fileinfo in zf.infolist():
        with zf.open(fileinfo) as odxfile:
            odx_content = odxfile.read()
            return extractodx.extract_odx(odx_content, flash_info, is_dsg)
