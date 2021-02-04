import os

libdir = os.path.dirname(os.path.abspath(__file__))

def main(inputfile = '', outputfile = ''):

    command = libdir + "/lzss/lzss -i " + inputfile + " -o " + outputfile
    result = os.system(command)

