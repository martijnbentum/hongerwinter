import sys
import glob
from .add import Papers
from django.core.management.base import BaseCommand, CommandError

directory = '/vol/tensusers/mbentum/hongerwinter/oai2linerec/hongerwinter/'

class Command(BaseCommand):
	help = 'parses newspaper documents and loads them in the database'
	
	def handle_file(self):
		fn = get_filenames_kranten() + get_filenames_ddd()

def get_filenames_ddd():
	return glob.glob(directory+'ddd-*-ocr')

def get_filenames_kranten():
	return glob.glob(directory+'kranten-*-ocr')

def add_done_file(name):
	with open(directory+'done_files','a') as fout:
		fout.write(name +'\n')

def get_done_files():
	with open(directory+'done_files','r') as fin:
		return [f for f in fin.read().split('\n')]


def set_reserved_file(name):
	with open(directory+'reserved_files','a') as fout:
		fout.write(name +'\n')

def get_reserved_files():
	with open(directory+'reserved_files','r') as fin:
		return [f for f in fin.read().split('\n')]


