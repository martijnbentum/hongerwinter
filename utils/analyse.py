#!/usr/local/bin/python
# -*- coding: utf-8 -*-

from collections import Counter
from datetime import datetime
import glob
import gc
from lxml import etree
import multiprocessing
import ucto #assumes lamachine is loaded
import os
from parse_results import get_time
import pickle

cf ="tokconfig-nld"
t = ucto.Tokenizer(cf,lowercase = True)


def get_stop_words():
	stop_words = open('stop-words').read().split('\n')
	return stop_words

def pickle_save(o,name):
	pickle.dump(o,open(name,'wb'))

def pickle_load(name):
	return pickle.load(open(name,'rb'))

def get_filenames_ddd():
	return glob.glob('ddd-*-ocr')

def get_filenames_kranten():
	return glob.glob('kranten-*-ocr')

def check_vocabulary_done(filename):
	if not os.path.isfile('vocabulary_done_files'): 
		fout = open('vocabulary_done_files','w')
		fout.close()
	fn = open('vocabulary_done_files').read().split('\n')
	return filename in fn

def add_vocabulary_done(filename):
	with open('vocabulary_done_files','a') as fout:
		fout.write(filename + '\n')

def load_latest_vocabulary():
	fn = glob.glob('vocabulary*')
	print('found the following vocabulary files:',' '.join(fn))
	latest = ''
	highest = -1
	for f in fn:
		try: n = int(f.split('_')[-1])
		except: continue
		if n > highest: 
			latest = f
			highest = n
	if latest == '': return False
	print('loading:',latest,'vocabulary')
	v = pickle_load(latest)
	print('loading done')
	return v


	

def make_vocabulary(use_stopwords = True,add_location = True):
	if type(use_stopwords) == list:pass
	else: stop_words = get_stop_words() if use_stopwords else []
	print('using location:',add_location,' use stop_words:',stop_words,get_time())
	v = load_latest_vocabulary()
	if not v:
		print('could not find vocabulary, creating a new empty vocabulary')
		v = Vocabulary(do_add_location=add_location, stop_words = stop_words)
	filenames = get_filenames_kranten() + get_filenames_ddd()
	for i,f in enumerate(filenames):
		if check_vocabulary_done(f):
			print(f, 'already done',get_time())
			continue
		print(f,len(filenames),i)
		papers = Papers(f)
		print('loaded:',f,get_time())
		try:papers.clean_texts
		except:print('could not do multiprocessing load',get_time())
		v.add_papers(papers)
		add_vocabulary_done(f)
		del papers
		gc.collect()
		pickle_save(v,'vocabulary_'+str(i))
	return v

class Vocabulary:
	def __init__(self, do_add_location =False,stop_words = [], include_words = []):
		self.words ={}
		self.do_add_location = do_add_location
		self.stop_words = stop_words
		self.include_words = include_words
		if include_words: self.check_include_words = True
		else: self.check_include_words = False

	def __getitem__(self,key):
		return self.words[key]

	def __setitem__(self,key,item):
		self.words[key] = Word(item)

	def __getstate__(self):
		return self.__dict__

	def __setstate__(self,d):
		self.__dict__ = d

	def __repr__(self):
		return 'vocabulary with: '+str(len(self.words))+' words'

	def keys(self):
		return self.words.keys()

	def add_word_time_count(self,word,dt,count):
		if not word in self.words.keys(): self[word] = word
		self.words[word].add_time_count(dt,count)
		
	def add_location(self,word,identifier,article_index,filename):
		if not word in self.words.keys(): self[word] = word
		self.words[word].add_location(identifier,article_index,filename)

	def add_paper(self,paper,filename=''):
		for i,article in enumerate(paper.articles):
			for word,count in article.word_frequency.items():
				if word in self.stop_words: continue
				if self.check_include_words and word not in self.include_words: continue
				self.add_word_time_count(word,paper.dt,count)
				if self.do_add_location:self.add_location(word,paper.identifier,i,filename)

	def add_papers(self,papers):
		for i,paper in enumerate(papers.papers):
			if i > 0 and i % 100 == 0:print('handling paper:',i,len(papers.papers))
			self.add_paper(paper,papers.filename)

class Word:
	def __init__(self,word):
		self.word = word
		self.year = {}
		self.yearmonth = {}
		self.yearmonthday = {}
		self.locations = {}
		self.nlocations = 0

	def __repr__(self):
		return str(self.count)

	def __getstate__(self):
		return self.__dict__

	def __setstate__(self,d):
		self.__dict__ = d

	def add_time_count(self,dt,count):
		if dt.year in self.year:
			self.year[dt.year] += count
		else: self.year[dt.year] = count
		if (dt.year,dt.month) in self.yearmonth.keys():
			self.yearmonth[(dt.year,dt.month)] += count
		else: self.yearmonth[(dt.year,dt.month)] = count 
		if (dt.year,dt.month,dt.day) in self.yearmonthday.keys():
			self.yearmonthday[(dt.year,dt.month,dt.day)] += count
		else: self.yearmonthday[(dt.year,dt.month,dt.day)] = count 

	def add_location(self,identifier,article_index,filename):
		if filename not in self.locations.keys(): self.locations[filename] = {}
		if identifier not in self.locations[filename].keys(): self.locations[filename][identifier] = []
		self.locations[filename][identifier].append( article_index )
		self.nlocations += 1

	@property
	def count(self):
		return sum(self.year.values())
	
	


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

	def _make_clean_texts(self):
		self._clean_text = []
		for paper in self.papers:
			self._clean_text.extend(paper.clean_texts)

	def _make_clean_texts_multi(self):
		print('start multiprocessing...')
		p = multiprocessing.Pool(27)
		self.papers = p.map(make_ct,self.papers)
		p.close()
		p.join()
		print('done multiprocessing!')
		del p
		self._make_clean_texts()

	@property
	def clean_texts(self):
		if not hasattr(self,'_clean_text'):self._make_clean_texts_multi()
		return self._clean_text

	def _make_word_frequency(self):
		for i,paper in enumerate(self.papers):
			if i == 0:self._word_frequency = Counter(paper.word_frequency)
			else: self._word_frequency += Counter(paper.word_frequency)

	def _make_word_frequency_multi(self):
		print('start multiprocessing...')
		p = multiprocessing.Pool(30)
		self.papers = p.map(make_wf,self.papers)
		p.close()
		p.join()
		print('done multiprocessing!')
		del p
		self._make_word_frequency()

	@property
	def word_frequency(self):
		if not hasattr(self,'_word_frequency'): self._make_word_frequency_multi()
		return self._word_frequency

def make_wf(paper):
	paper.word_frequency
	return paper

def make_ct(paper):
	paper.clean_texts
	return paper

	
class Paper:
	def __init__(self,t):
		self.xml = etree.fromstring('<paper>'+t)
		self._set_info()
		self._make_articles()

	def __repr__(self):
		return self.title + '\t' + self.date + '\t' + self.language

	def __getstate__(self):
		self._remove_extra()
		return self.__dict__

	def __setstate__(self,d):
		self.__dict__ = d

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

	@property
	def clean_texts(self):
		return [article.clean_text for article in self.articles]

	def _make_word_frequency(self):
		self._word_frequency = Counter()
		for i,article in enumerate(self.articles):
			if i == 0:self._word_frequency = Counter(article.word_frequency)
			else: self._word_frequency += Counter(article.word_frequency)

	@property
	def word_frequency(self):
		if not hasattr(self,'_word_frequency'): self._make_word_frequency()
		return self._word_frequency

	def _remove_extra(self):
		names = 'xml'
		for name in names.split(','):
			if hasattr(self,name):delattr(self,name)


class Article:
	def __init__(self,xml):
		self.xml = xml
		self._set_info()

	def __repr__(self):
		return self.title 

	def __str__(self):
		m = self.__repr__() + '\n'
		m += self.text
		return m

	def __getstate__(self):
		self._remove_extra()
		return self.__dict__

	def __setstate__(self,d):
		self.__dict__ = d


	def _set_info(self):
		for e in self.xml.getchildren():
			setattr(self,e.tag,e.text)


	def _make_clean_text(self):
		if not self.text:
			self.tokens,self.words,self.word_types,self.sentences,self._clean_text = [],[],[],[],''
			return
		t.process(self.text.lower())
		self.tokens = list(t)
		self.words = [str(t).replace('-','') for t in self.tokens if 'WORD' in t.tokentype]
		self.word_types = list(set(self.words))
		self.sentences,sentence = [],[]
		for token in self.tokens:
			if 'WORD' in token.tokentype:sentence.append(str(token).replace('-',''))
			if token.isendofsentence():
				self.sentences.append(' '.join(sentence))
				sentence = []
		self._clean_text = '\n'.join(self.sentences)

	@property
	def clean_text(self):
		if not hasattr(self,'_clean_text'): self._make_clean_text()
		return self._clean_text


	def _make_word_frequency(self):
		if not hasattr(self,'_clean_text'): self._make_clean_text()
		self._word_frequency = {}
		for word in self.word_types:
			self._word_frequency[word] = self.words.count(word)

	@property
	def word_frequency(self):
		if not hasattr(self,'_word_frequency'): self._make_word_frequency()
		return self._word_frequency

	def _remove_extra(self):
		names = 'xml,tokens'
		for name in names.split(','):
			if hasattr(self,name):delattr(self,name)
		


	

