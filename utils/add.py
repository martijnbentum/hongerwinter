from django.db import IntegrityError
from collections import Counter
from datetime import datetime
import glob
import gc
from lxml import etree
import os
from vocabulary.models import Paper as p
from vocabulary.models import Article as a

def get_filenames_ddd():
	return glob.glob('ddd-*-ocr')

def get_filenames_kranten():
	return glob.glob('kranten-*-ocr')



class Papers:
	def __init__(self,filename='',t=''):
		if filename == t == '':raise ValueError('provide filename or string')
		if filename:
			self.filename = filename
			t = open(filename).read()
		self.papers = [Paper(tt) for tt in t.split('<paper>')[1:]]
		self.id2paper = dict([[paper.identifier,paper] for paper in self.papers if hasattr(paper,'identifier')])
		self.npapers = len(self.papers)

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
		for article in self.articles:
			article.make(self.paper)
			
	def make(self):
		self._make_paper()
		self._make_db_articles()
		self.article_errors = sum([a.integrity_error for a in self.articles])


class Article:
	def __init__(self,xml):
		self.xml = xml
		self._set_info()
		self.integrity_error = False

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
		self.article = a(
			a_paper = paper,
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
		
