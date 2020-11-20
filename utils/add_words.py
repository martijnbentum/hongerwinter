from django.db import IntegrityError
from collections import Counter
from datetime import datetime
import glob
from vocabulary.models import Paper, Article, Word 
from vocabulary.models import WordArticleRelation as war
import time
try:
	import ucto
	tokenizer = ucto.Tokenizer("tokconfig-nld",lowercase = True,
		sentencedetection=False,paragraphdetection=False)
except:
	print('could not load ucto')
	tokenizer = ''

directory = '/vol/tensusers/mbentum/hongerwinter/oai2linerec/hongerwinter/'


lnd = dict([line.split('\t') for line in open('location_names_dict').read().split('\n') if line])

def add_done_paper(name,location_category= 'landelijk',hw = True):
	hw = '_hongerwinter' if hw else '_no_hongerwinter'
	with open(directory+'done_papers_'+location_category+hw,'a') as fout:
		fout.write(name +'\n')

def get_done_paper(location_category='landelijk', hw = True):
	hw = '_hongerwinter' if hw else '_no_hongerwinter'
	with open(directory+'done_papers_'+location_category+hw,'r') as fin:
		return [f for f in fin.read().split('\n') if f]

def add_location_category():
	for p in Paper.objects.all():
		p.location_category = lnd[p.location]
		p.save()


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
		w = Word(word = word)
		save2db(w,excists,error,ok)
	print('created words, already exists:',len(excists),'saved:',len(ok),'error:',len(error))
	print(' | '.join(lexicon))
	return excists,error,ok



def add_all_word_article_relations(lexicon=[], location_category='landelijk',check_hw = True):
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
		if location_category == 'all':print('handling all location_categories')
		elif x.location_category != location_category: 
			print('skipping paper with location category:',x.location_category)
			continue
		if x.link in get_done_paper(location_category,check_hw): 
			print('skipping paper',x,'already done')
			continue
		date = x.date
		articles = x.article_set.all()
		print('starting with paper',x,'with ',len(articles),' from ',date)
		if i != 0:print(eta(start,i,npapers))
		for article in articles:
			add_word_article_relations(words,article,date,excists,error,ok,check_hw)
		add_done_paper(x.link,location_category,check_hw)
		
	set_category_done(words,location_category)
	print('created words, already exists:',len(excists),'saved:',len(ok),'error:',len(error))
	return excists,error,ok


def check_word_occurence(word,article_text,td=None):
	'''check whether hongerwinter and the target word occurs in the text.
	returns the number of time the target word occurred in the text'''
	if td == None:td = article2counter(article)
	hw_count = td['hongerwinter'] if 'hongerwinter' in td.keys() else 0
	if ' ' in word.word: count = article_text.count(word.word)
	else: count = td[word.word] if word.word in td.keys() else 0
	return count, hw_count
			

def add_word_article_relations(words,article,date,excists=[],error=[],ok=[],check_hw = True):
	'''check for each word the number of times it occurs in the article
	create wordArticleRelation object that stores word, article, date & count info.
	'''
	td = article2counter(article)
	article_text = article.text.lower()
	for word in words:
		count,hongerwinter_count = check_word_occurence(word,article_text,td)
		if check_hw and hongerwinter_count == 0: continue
		if count == 0: continue
		relation = war(article = article, word = word,count = count,date = date)
		save2db(relation,excists,error,ok)
		
	
def article2tokens(article):
	tokenizer.process(article.text)
	return  [str(token).lower() for token in tokenizer]
	
def article2counter(article):
	tokens = article2tokens(article)
	return Counter(tokens)


def get_words(lexicon=[],location_category='landelijk'):
	'''Save words in the lexicon to the database, load the words from the database
	exclude the words have already been handle for the location category
	return list of words that are not yet handled for the location_category
	'''
	if lexicon == []:lexicon = get_lexicon()
	add_lexicon(lexicon)
	temp= [Word.objects.get(word=word) for word in lexicon]
	words = []
	for word in temp:
		if check_done(word,location_category): continue
		else: words.append(word)
	return words

def check_done(word,location_category):
	'''check whether a word has already been processed (all word article relation been added)
	for the current location category
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
	elif location_category == 'regionaal':attr='regional'
	elif location_category == 'koloniaal':attr='colonial'
	else: raise ValueError(location_category+ 
		' unknown, should be landelijk, regionaal or koloniaal')
	for word in words:
		setattr(word,attr,True)
		save2db(words)
	print('set',attr,'to true for the following words:\n',' '.join([w.word for w in words]))





#-- time helper function, estimate time the function call is done
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

