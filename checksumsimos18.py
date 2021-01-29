import sys, getopt
import binascii
import zlib
import struct
import logging

import lib.checksum as checksum

if __name__ == "__main__":
   simos12 = False
   inputfile = ''
   outputfile = ''
   try:
      opts, args = getopt.getopt(sys.argv[1:],"h2i:o:b:",["help","simos12","ifile=","ofile=","blocknum="])
   except getopt.GetoptError:
      print('checksumsimos18.py -i <inputfile> -o <outputfile>')
      sys.exit(2)

   for opt, arg in opts:
      if opt in ("-h", "--help"):
         print('checksumsimos18.py -i <inputfile> -o <outputfile>')
         sys.exit()
      elif opt in ("-2", "--simos12"):
         simos12 = True
      elif opt in ("-i", "--ifile"):
         inputfile = arg
      elif opt in ("-o", "--ofile"):
         outputfile = arg
      elif opt in ("-b", "--blocknum"):
         blocknum = int(arg)


   result = checksum.main(simos12 = simos12, inputfile = inputfile, outputfile = outputfile, blocknum = blocknum, loglevel = logging.INFO)
