import sys, getopt
from Crypto.Cipher import AES
import binascii

def main(argv):
   inputfile = ''
   outputfile = ''
   try:
      opts, args = getopt.getopt(argv,"hi:o:",["ifile=","ofile="])
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
   print("Encrypting " + inputfile + " to " + outputfile)
   key = binascii.unhexlify('98D31202E48E3854F2CA561545BA6F2F')
   iv = binascii.unhexlify('E7861278C508532798BCA4FE451D20D1')
   f = open(inputfile, "rb")
   dataBinary = f.read()    
   cipher = AES.new(key, AES.MODE_CBC, iv)
   cryptedContent = cipher.encrypt(dataBinary)
   with open(outputfile, 'wb') as fullDataFile:
      fullDataFile.write(cryptedContent)

if __name__ == "__main__":
   main(sys.argv[1:])
