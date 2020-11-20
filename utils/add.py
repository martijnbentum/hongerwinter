from django.db import IntegrityError
from collections import Counter
from datetime import datetime
import glob
import gc
from lxml import etree
import os
from vocabulary.models import Paper as p
from vocabulary.models import Article as a

lnd = dict([line.split('\t') for line in open('location_names_dict').read().split('\n') if line])

directory = '/vol/tensusers/mbentum/hongerwinter/oai2linerec/hongerwinter/'

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


def handle():
	for f in get_filenames_kranten() + get_filenames_ddd():
		done = get_done_files() 
		if f in done:
			print(f,'already done moving to next file')
			continue
		set_reserved_file(f)
		print('making paper object:',f)
		p = Papers(f)
		print('loading files in database')
		print('npapers:',p.npapers)
		print('narticles:',p.narticles)
		p.make()
		print('paper integrity error:',p.paper_errors)
		print('article integrity error:',p.article_errors)
		print('article no text:',p.no_text)
		print('-'*80)
		print('')
		log(p,f)
		add_done_file(f)

def log(p,f):
	m = '\nmaking paper object:'+f+'\n'
	m+='npapers:'+str(p.npapers)+'\n'
	m+='narticles:'+str(p.narticles)+'\n'
	m+='paper integrity error:'+str(p.paper_errors)+'\n'
	m+='article integrity error:'+str(p.article_errors)+'\n'
	m+='article no text:'+str(p.no_text)+'\n'
	m+=f+'\n'
	m+='-'*80+'\n'
	with open(directory+'db_log','a') as fout:
		fout.write(m+'\n')

def log_message(m):
	with open(directory+'db_log','a') as fout:
		fout.write(m+'\n')

class Papers:
	def __init__(self,filename='',t=''):
		if filename == t == '':raise ValueError('provide filename or string')
		if filename:
			self.filename = filename
			t = open(filename).read()
		self.papers = [Paper(tt) for tt in t.split('<paper>')[1:]]
		self.id2paper = dict([[paper.identifier,paper] for paper in self.papers if hasattr(paper,'identifier')])
		self.npapers = len(self.papers)
		self.narticles= sum([int(p.narticles) for p in self.papers])

		self.paper_errors =0
		self.article_errors =0
		self.no_text= 0

	def __repr__(self):
		return str(self.papers[0].dt.year)

	def __getitem__(self,key):
		return self.id2paper[key]

	def keys(self):
		return self.id2paper.keys()

	def make(self):
		for paper in self.papers:
			paper.make()
		self.paper_errors = sum([p.integrity_error for p in self.papers])
		self.article_errors = sum([p.article_errors for p in self.papers])
		self.no_text= sum([p.no_text for p in self.papers])


class Paper:
	def __init__(self,t):
		self.xml = etree.fromstring('<paper>'+t)
		self._set_info()
		self._make_articles()
		self.integrity_error = False

	def __repr__(self):
		return self.title + '\t' + self.date + '\t' + self.language

	def _set_info(self):
		info = self.xml.find('paper_info')
		for e in info.getchildren():
			setattr(self,e.tag,e.text)

	def _make_articles(self):
		articles = self.xml.findall('article')
		self.articles = []
		for article in articles:
			self.articles.append(Article(article))

	@property
	def dt(self):
		return  datetime.strptime(self.date,'%Y-%m-%d')

	def _make_paper(self):
		self.paper = p(
			title= self.title,
			location= self.spatial,
			location_category = lnd[self.spatial] if self.spatial in lnd.keys() else 'na',
			language= self.language,
			ids = self.identifier,
			link = self.link,
			narticles= int(self.narticles),
			nexcluded_articles = int(self.nexcluded_articles),
			excluded_article_ids = self.excluded_articles_id,
			nerrors = int(self.nerrors),
			nword_tokens = int(self.nwords),
			date = self.dt)
		try:self.paper.save()
		except IntegrityError: self.integrity_error = True
		
	def _make_db_articles(self):
		if not hasattr(self,'paper'):self._make_paper()
		if self.integrity_error:return
		for article in self.articles:
			article.make(self.paper)
			
	def make(self):
		self._make_paper()
		self._make_db_articles()
		self.article_errors = sum([a.integrity_error for a in self.articles])
		self.no_text= sum([a.no_text for a in self.articles])


class Article:
	def __init__(self,xml):
		self.xml = xml
		self._set_info()
		self.integrity_error = False
		self.value_error = False
		self.no_text = False

	def __repr__(self):
		return self.title 

	def __str__(self):
		m = self.__repr__() + '\n'
		m += self.text
		return m

	def _set_info(self):
		for e in self.xml.getchildren():
			setattr(self,e.tag,e.text)

	def _make_article(self,paper):
		if self.text == None:
			self.no_text = True
			return
		self.article = a(
			paper = paper,
			title = self.title,
			link = self.link,
			text = self.text,
			subject = self.subject,
			page = self.page,
			date = paper.date)
		try: self.article.save()
		except IntegrityError: self.integrity_error = True
	

	def make(self,paper):
		self._make_article(paper)
		
