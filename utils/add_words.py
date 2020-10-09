from django.db import IntegrityError
from collections import Counter
from datetime import datetime
import glob
from vocabulary.models import Paper, Article, Word 
from vocabulary.models import WordArticleRelation as war
import time
import ucto

tokenizer = ucto.Tokenizer("tokconfig-nld",lowercase = True,
	sentencedetection=False,paragraphdetection=False)

def save2db(item,excists=[],error=[],ok=[]):
	try: item.save()
	except IntegrityError: excists.append(item)
	except: error.append(item)
	else: ok.append(item)
	

def get_lexicon():
	return [w.strip().lower() for w in open('lexicon').read().split('\n') if w]

def add_lexicon(lexicon = []):
	if lexicon == []:lexicon = get_lexicon()
	excists,error,ok = [],[],[]
	for word in lexicon:
		w = Word(w_word = word)
		save2db(w,excists,error,ok)
	print('created words, already exists:',len(excists),'saved:',len(ok),'error:',len(error))
	print(' '.join(lexicon))

def delta_time(start):
	return time.time() - start

def add_zero(t):
	t = str(t)
	if len(t) == 1: t ='0'+t
	return t

def seconds2time(etas):
	days = int(etas / (3600*24))
	remaining = etas % (3600*24)
	hours = add_zero(int(remaining / 3600)) 
	remaining = remaining % 3600
	minutes = add_zero(int(remaining /60))
	t = hours + ':' + minutes
	return 'time remaining: ' + str(days) + ' days, '+ t

def eta(start,index,n):
	dt = delta_time(start)
	estimate_per_unit = dt / index+1
	n_togo = n - (index+1)
	etas = n_togo*estimate_per_unit
	return seconds2time(etas) + ' | index: '+str(index) + ' total: '+str(n)


def add_all_word_article_relations(lexicon=[], location_category='landelijk'):
	'''add word article relations for articles in the database that are
	published in a newspaper corresponding to the location category, 
	for each word in the lexicon.
	'''
	words = get_words(lexicon,location_category)
	if not words:
		print('words done for category:',location_category,'\n',' '.join(lexicon))
		return
	excists,error,ok = [],[],[]
	papers = Paper.objects.all()
	npapers = len(papers)
	start = time.time()
	for i,x in enumerate(papers):
		date = x.date
		articles = x.article_set.all()
		print('starting with paper',x,'with ',len(articles),' from ',date)
		if i != 0:print(eta(start,i,npapers))
		for article in articles:
			add_word_article_relations(words,article,date,excists,error,ok)
		
	set_category_done(words,location_category)
	print('created words, already exists:',len(excists),'saved:',len(ok),'error:',len(error))
	return excists,error,ok
			

def add_word_article_relations(words,article,date,excists=[],error=[],ok=[]):
	'''check for each word the number of times it occurs in the article
	create wordArticleRelation object that stores word, article, date & count info.
	'''
	td = article2counter(article)
	for word in words:
		w = word.w_word
		if w not in td.keys():continue
		relation = war(war_article = article, war_word = word,count = td[w],date = date)
		save2db(relation)
		
	
def article2tokens(article):
	tokenizer.process(article.text)
	return  [str(token).lower() for token in tokenizer]
	
def article2counter(article):
	tokens = article2tokens(article)
	return Counter(tokens)


def get_words(lexicon,location_category):
	'''Save words in the lexicon to the database, load the words from the database
	exclude the words have already been handle for the location category
	return list of words that are not yet handled for the location_category
	'''
	if lexicon == []:lexicon = get_lexicon()
	add_lexicon(lexicon)
	temp= [Word.objects.get(w_word=word) for word in lexicon]
	words = []
	for word in temp:
		if check_done(word,location_category): continue
		else: words.append(word)
	return words

def check_done(word,location_category):
	'''check whether a word has already been processed (all word article relation been added)
	for the current location strategy
	'''
	if location_category == 'landelijk':return word.national
	if location_category == 'regionaal':return word.regional
	if location_category == 'koloniaal':return word.colonial
	else: raise ValueError(location_category+
		' unknown, should be landelijk, regionaal or koloniaal')
		
def set_category_done(words,location_category):
	'''set category done for each word in words.
	'''
	if location_category == 'landelijk':attr='national'
	if location_category == 'regionaal':attr='regional'
	if location_category == 'koloniaal':attr='colonial'
	else: raise ValueError(location_category+ 
		' unknown, should be landelijk, regionaal or koloniaal')
	for word in words:
		setattr(word,attr,True)
	print('set',attr,'to true for the following words:\n',' '.join([w.w_word for w in words]))

