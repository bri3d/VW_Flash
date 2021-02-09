import os
import subprocess

libdir = os.path.dirname(os.path.abspath(__file__))

def lzss_compress(input_data: bytes) -> bytes:
    p = subprocess.run([libdir + "/lzss/lzss", "-s"], input=input_data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output_data = p.stdout
    return output_data

def main(inputfile = '', outputfile = ''):
    command = libdir + "/lzss/lzss -i " + inputfile + " -o " + outputfile
    result = os.system(command)