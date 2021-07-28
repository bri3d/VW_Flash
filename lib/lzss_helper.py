import os, sys
import subprocess

if sys.platform == "win32":
    libdir = os.path.dirname(os.path.abspath(sys.argv[0]))
else:
    libdir = os.path.dirname(os.path.abspath(__file__))


def lzss_compress(input_data: bytes) -> bytes:
    if sys.platform == "win32":
        lzssPath = "/lib/lzss/lzss.exe"
    else:
        lzssPath = "/lzss/lzss"

    p = subprocess.run(
        [libdir + lzssPath, "-s"],
        input=input_data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    output_data = p.stdout
    return output_data


def main(inputfile="", outputfile=""):
    command = libdir + "/lzss/lzss -i " + inputfile + " -o " + outputfile
    result = os.system(command)
