import sys
import subprocess

from .resource_helper import resource_path


def lzss_compress(input_data: bytes, skip_padding=False, exact_padding=False) -> bytes:
    if sys.platform == "win32":
        lzss_name = "lzss.exe"
    else:
        lzss_name = "lzss"

    lzss_path = resource_path("lib/lzss/" + lzss_name)

    lzss_command_line = [lzss_path, "-s"]

    # Don't pad up to the AES blocksize. Used for DSG
    if skip_padding:
        lzss_command_line.append("-p")
    if exact_padding:
        lzss_command_line.append("-e")

    p = subprocess.run(
        lzss_command_line,
        input=input_data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    output_data = p.stdout
    return output_data
