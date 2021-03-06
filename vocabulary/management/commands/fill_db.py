import sys
import glob
from utils.add import Papers
from django.core.management.base import BaseCommand, CommandError

directory = '/vol/tensusers/mbentum/hongerwinter/oai2linerec/hongerwinter/'

class Command(BaseCommand):
	help = 'parses newspaper documents and loads them in the database'
	
	def handle(self,*args,**options):
		fn = get_filenames_kranten() + get_filenames_ddd()
		done = get_done_files() + get_reserved_files()
		finished=True
		self.stdout.write('done files')
		self.stdout.write('\n'.join(done))
		for f in fn:
			if f not in done: 
				finished= False
				break
		if not finished:
			set_reserved_file(f)
			self.stdout.write('start work on: '+f)
			p = Papers(filename = f)
			p.make()
			self.stdout.write('paper integrity errors: '+str(p.paper_errors))
			self.stdout.write('article integrity errors: '+str(p.article_errors))
			add_done_file(f)
		else: 
			self.stdout.write('all done')

		

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
