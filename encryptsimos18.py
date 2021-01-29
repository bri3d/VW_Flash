import sys, getopt
from Crypto.Cipher import AES
import binascii
import lib.encrypt as encrypt
import logging


inputfile = ''
outputfile = ''
try:
   opts, args = getopt.getopt(sys.argv[1:],"hi:o:",["ifile=","ofile="])
except getopt.GetoptError:
   print('encryptsimos18.py -i <inputfile> -o <outputfile>')
   sys.exit(2)
for opt, arg in opts:
   if opt == '-h':
      print('encryptsimos18.py -i <inputfile> -o <outputfile>')
      sys.exit()
   elif opt in ("-i", "--ifile"):
      inputfile = arg
   elif opt in ("-o", "--ofile"):
      outputfile = arg


result = encrypt.main(inputfile = inputfile, outputfile = outputfile, loglevel = logging.DEBUG)


