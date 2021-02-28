import os, sys
import subprocess

libdir = os.path.dirname(os.path.abspath(__file__))



def lzss_compress(input_data: bytes) -> bytes:
    if sys.platform == "win32":
        #import msvcrt
        p = subprocess.run([libdir + "/lzss/lzss.exe", "-s"], input=input_data, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        #msvcrt.setmode(p.stdout.fileno(  ), os.O_BINARY)
        
        output_data = p.stdout
        return output_data

def main(inputfile = '', outputfile = ''):
    command = libdir + "/lzss/lzss -i " + inputfile + " -o " + outputfile
    result = os.system(command)