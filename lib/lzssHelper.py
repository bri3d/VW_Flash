import os
from subprocess import Popen, PIPE, STDOUT

libdir = os.path.dirname(os.path.abspath(__file__))

def lzss_compress(input_data: bytes) -> bytes:
    p = Popen([libdir + "/lzss/lzss", "-s"], stdout=PIPE, stdin=PIPE, stderr=PIPE)
    output_data = p.communicate(input=input_data)[0]
    return output_data

def main(inputfile = '', outputfile = ''):

    command = libdir + "/lzss/lzss -i " + inputfile + " -o " + outputfile
    result = os.system(command)

