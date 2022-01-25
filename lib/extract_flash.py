import io
import zipfile
from frf import decryptfrf
import extractodx
from . import constants


def extract_flash_from_frf(
    frf_data: bytes, flash_info: constants.FlashInfo, is_dsg=False
):
    odx_data = extract_odx_from_frf(frf_data)
    return extract_data_from_odx(odx_data, flash_info, is_dsg)


def extract_odx_from_frf(frf_data: bytes):
    decrypted_frf = decryptfrf.decrypt_data(decryptfrf.read_key_material(), frf_data)
    zf = zipfile.ZipFile(io.BytesIO(decrypted_frf), "r")

    for fileinfo in zf.infolist():
        with zf.open(fileinfo) as odxfile:
            odx_content = odxfile.read()
            return odx_content


def extract_data_from_odx(
    odx_content: bytes, flash_info: constants.FlashInfo, is_dsg=False
):
    return extractodx.extract_odx(odx_content, flash_info, is_dsg)
