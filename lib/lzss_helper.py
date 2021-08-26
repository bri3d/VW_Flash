import os, sys
import subprocess

if sys.platform == "win32":
    libdir = os.path.dirname(os.path.abspath(sys.argv[0]))
else:
    libdir = os.path.dirname(os.path.abspath(__file__))


def lzss_compress(input_data: bytes, skip_padding=False) -> bytes:
    if sys.platform == "win32":
        lzssPath = "/lib/lzss/lzss.exe"
    else:
        lzssPath = "/lzss/lzss"

    lzss_command_line = [libdir + lzssPath, "-s"]

    # Don't pad up to the AES blocksize. Used for DSG
    if skip_padding:
        lzss_command_line.append("-p")

    p = subprocess.run(
        lzss_command_line,
        input=input_data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    output_data = p.stdout
    return output_data


def main(inputfile="", outputfile=""):
    command = libdir + "/lzss/lzss -i " + inputfile + " -o " + outputfile
    result = os.system(command)
