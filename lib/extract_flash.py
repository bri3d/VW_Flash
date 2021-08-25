import io
import zipfile
from frf import decryptfrf
import extractodx
from . import constants


def extract_flash_from_frf(frf_data: bytes):
    decrypted_frf = decryptfrf.decrypt_data(decryptfrf.read_key_material(), frf_data)
    zf = zipfile.ZipFile(io.BytesIO(decrypted_frf), "r")

    for fileinfo in zf.infolist():
        with zf.open(fileinfo) as odxfile:
            odx_content = odxfile.read()
            try:
                return extractodx.extract_odx(odx_content, constants.s18_flash_info)
            except:
                return extractodx.extract_odx(odx_content, constants.s1810_flash_info)
