from distutils.core import setup
import py2exe
import lib

data_files = [("lib/lzss", ["lib/lzss/lzss.exe"]), (".", ["logging.conf"]), ("data", ["data/box_codes.csv"])]

setup(console=["VW_Flash_GUI.py"], data_files=data_files)
