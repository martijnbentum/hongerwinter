from vocabulary.models import WordArticleRelation as war
from vocabulary.models import Article,Paper,Word
from .add_words import article2counter, eta
import time

articles = []

class AllWordCounts:
	'''create counts for each year for different categories of newspapers.'''
	def __init__(self,filename = 'all_word_counts'):
		global articles
		print('init..')
		self.filename = filename
		if not articles:
			self.articles = list(Article.objects.all())
			articles = self.articles
		else: self.articles = articles
		self._make_counts()

	def _make_counts(self):
		self.regionaal, self.landelijk = {}, {}
		for name in 'decade,year,month'.split(','):
			self.regionaal[name],self.landelijk[name] = {}, {}
		print('counting...')
		narticles = len(self.articles)#32724636#len(self.articles)
		start = time.time()
		for i,article in enumerate(self.articles):
			print(eta(start,i,narticles))
			print(i,narticles,'\t',article)
			c = article2counter(article)
			if article.nword_types == None:
				article.nword_tokens = sum(c.values())
				article.nword_types = len(c.keys())
				article.save()
			self._fill_dicts(article,sum(c.values()))

	def _fill_dicts(self,article,count):
		lc = article.paper.location_category
		if lc not in 'landelijk,regionaal'.split(','): return
		date = article.date
		d = getattr(self,lc)
		t = make_decade(date.year)
		if t not in d['decade'].keys(): d['decade'][t] = 0
		if date.year not in d['year'].keys(): d['year'][date.year] = 0
		if (date.year,date.month) not in d['month'].keys(): d['month'][(date.year,date.month)] = 0
		d['decade'][t] += count
		d['year'][date.year] += count
		d['month'][(date.year,date.month)] += count




class WordInfos:
	'''create counts word words listed in the lexicon for each year.'''
	def __init__(self,filename = 'word_counts_time'):
		self.filename = filename

	def make_word_counts(self):
		self.words = Word.objects.all()
		self.wi = {}
		for word in self.words:
			print('counting:',word)
			self.wi[str(word)] = WordInfo(word)

	def save(self):
		o = {}
		for word in self.words:
			d = {}
			for t in 'decade,year,month'.split(','):
				d[t] = getattr(self.wi[str(word)],t)
			o[str(word)] = str(d)
		with open(self.filename,'w') as fout:
			fout.write(str(o))
		self.output_dict = o
		return o

def load(self):
	with open(self.filename) as fin:
		self.text = fin.read()
	self.dict = eval(self.text)
	for word in self.dict.keys():
		self.dict[word] = eval(self.dict[word])
			
			



class WordInfo:
	def __init__(self,word):
		self.word = word
		self._make_dicts()

	def _make_dicts(self):
		self.word_dict = make_word_dict(self.word)
		decade,year,month =  {},{},{}
		for key in self.word_dict.keys():
			t = make_decade(key.year)
			if t not in decade.keys(): decade[t] = 0
			if key.year not in year.keys(): year[key.year] = 0
			if (key.year,key.month) not in month.keys(): month[(key.year,key.month)] = 0
			decade[t] += self.word_dict[key]
			year[key.year] += self.word_dict[key]
			month[(key.year,key.month)] += self.word_dict[key]
		self.decade,self.year,self.month = decade,year,month

def make_decade(year):
	s = str(year)
	if int(s[-1]) < 5: return int(s[:3] + '0')
	if s[2] == '9': return 2000
	return int(s[:2] + str(int(s[2])+1) + '0')



def make_word_dict(word):
	o = {}
	wr = war.objects.all()
	word = str(word)
	word_articles = [x for x in wr if x.word.word == word]
	for wa in word_articles:
		if wa.date not in o.keys():o[wa.date] = 0
		o[wa.date] += wa.count
	return o

