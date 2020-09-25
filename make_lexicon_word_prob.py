import glob
import numpy as np
import os
import random
import threading
import time

'''Get the probability distribution at each point in a text based on srilm ngram.
Step through a text sentence by sentence.
Extract precontexts upto 3 words (assumes 4gram model).
For each unique precontext make a string with the precontext and add a word from the lexicon
	do this for all words in the lexicon
output is called lexicon_text

For example:
sentence: how are you doing today
lexicon: bus, ship, taxi, house, ... (n = 10**6)
precontexts: how, how are, how are you, are you doing 

lexicon_text for precontext 'how':
how bus
how ship
how taxi
...

lexicon_text for precontext 'how are':
how are bus
how are ship
how are taxi
...

...

Each unique precontext is saved (temporarily) as a lexicon text 
srilm ngram call to generate ppl file with debug 2
the logprob for each lexicon word is extracted

in the case:
'how bus' the logprob for bus is extracted from the srilm output
logprobs for each word in the lexicon is extracted from ppl output

lexicon_text and ppl files are deleted, logprobs are kept as a numpy array
index of numpy array corresponds to word index in lexicon
'''


def sentence2lexicon_text(sentence,lexicon,only_precontext= False):
	'''Create alle precontext in the sentence (upto 3 words) and for each add all lexicon words.'''
	output,precontext= [],[None]
	words = sentence.split(' ')
	if len(words) == 1: return [1], None
	wi = dict(zip(list(range(len(words))),words))
	for i,word in enumerate(words):
		if i == 0: output.append([word,1])
		elif word not in lexicon or word == 'ggg': output.append([word,'OOV'])
		else:
			start = i -3
			if start < 0: start = 0
			precontext.append(' '.join(words[start:i]))
			if not only_precontext:output.append([word,[' '.join(words[start:i]+[w]) for w in lexicon]])
	if only_precontext: return precontext 
	return output, precontext


def save_lexicon_text(name,ls):
	'''save precontext (upto 3 words) + each word from the lexicon.'''
	print('saving lexicon text to:',name)
	with open(name,'w') as fout: fout.write('\n'.join(ls))
	os.system('touch DONE_LT/'+filename2name(name))


def load_lexicon():
	'''Load lexicon with all words with cumulative probability < .9 ~ 90k words.
	if a different lexicon is used other directories need to be specified
	'''
	return open('lexicon_cow_clean10_s90',encoding = 'utf8').read().split('\n')


	
def handle_text(text,lexicon = None,lm_name = '',lt_dir = '',ppl_dir = '',pdf_dir= '',overwrite =False, remove = True, max_nthreads = 10):
	'''Step through a text sentence by sentence to compute word pdf at each word.
	text 	 	list of sentences
	lexicon 	list words, order is important, ordor of word == order of word probs
	lm_name 	srilm language model to use
	lt_dir 		lexicon_text dir, each unique precontext is pasted before each word in lexicon
				files are stored in this directory
	ppl_dir 	ngram debug -2 output on lexicon text is stored here
	pdf_dir 	np_array of each lexicon word given a specific context is stored in the directory
	overwrite 	whether to overwrite previously created files
	remove 		whether to remove intermediate files, approx 1 terrabytes
	'''
	if lexicon == None: lexicon = load_lexicon()
	# if a different lexicon is used other directories need to be used
	else: assert '' not in [lt_dir,ppl_dir,pdf_dir] 
	# set default directories if they are not specified
	if lt_dir == '':lt_dir = 'LEXICON_TXT/'
	if ppl_dir == '':ppl_dir = 'PPL/'
	if pdf_dir == '':pdf_dir = 'PDF/'

	if overwrite: 
		for directory in ['DONE_LT/','DONE_PPL/','DONE_PDF/','KEEP/']:
			os.system('rm ' + directory + '*')
		if os.path.isfile('stop'): os.system('rm stop')
		time.sleep(3)

	#if no lexcion is specified, load default
	if lm_name == '': lm_name = 'cow_clean10.lm'
	#thread master holds all threads of all processes, to perform parallel computations 
	tm = thread_master(max_nthreads)
	#sentence index
	index = 0
	#whether all lexicon texts are made
	all_lt_done = False
	#the indices of sentences that are done or are processed
	accepted_indices = []
	nothing_to_be_done = False
	sentences = []
	last_print = 0
	to_do_ppl, to_do_pdf = [],[]
	while 1:
		if os.path.isfile('stop'): break
		if index < len(text): 
			sentence = text[index]
		else: all_lt_done = True
		if not all_lt_done or index not in accepted_indices and sentence not in sentences:
			# create lexicon texts of a sentence
			print('processing sentence:',sentence)
			job_accepted = tm.add_thread('lt',make_lexicon_text,(sentence,lexicon,lt_dir))
		if job_accepted and index < len(text): 
			accepted_indices.append(index)
			sentences.append(sentence)
			index += 1
			print('currently at index:',index,'of:',len(text),'\n',tm)
		# if there are lexicon text, these should be transformed to ppl file with ngram
		if tm.thread_available('ppl'):
			to_do_ppl = handle_ppl(tm,ppl_dir, lt_dir,lm_name,remove)
		# if there are ppl file, these should be transformed to pdf
		if tm.thread_available('pdf'):
			to_do_pdf = handle_pdf(tm, pdf_dir,ppl_dir,lexicon)
		if len(to_do_pdf) == len(to_do_ppl) == 0 and all_lt_done and not nothing_to_be_done:
			print('nothing to be done:', time.time())
			nothing_to_be_done = time.time()
		# if no new ppl and pdf files are made for 20 minutes after last lexicon text is made
		# stop the process
		if nothing_to_be_done and time.time() - nothing_to_be_done > 1800: break
		if time.time() - last_print > 10:
			last_print = time.time()
			print(tm)
			if nothing_to_be_done:
				print('waiting..',time.time() - nothing_to_be_done)
		time.sleep(3)
	print('finished working')
	return True
		
		
def handle_ppl(tm,ppl_dir, lt_dir,lm_name, remove = True):
	''' Transform any lexicon text (not yet processed) to ppl files. 
	tm 			thread_master
	ppl_dir 	location for ppl files (ngram debug -2 output) default lm name = 'cow_clean10.lm'
	lt_dir 		location for the lexicon texts
	remove 		whether to remove most files
	'''
	fn = glob.glob(lt_dir + '*')
	not_done = [f for f in fn if not check_ppl_done(filename2name(f))]
	if len(not_done) == 0: return []
	print('ppl handling files:',' '.join(not_done))
	for i,f in enumerate(not_done):
		name = filename2name(f)
		ppl_name = ppl_dir + name + '.ppl'
		print('ppl processing:',f,'saving to:',ppl_name)
		job_accepted = tm.add_thread('ppl',make_ppl,(f,ppl_name,lm_name, remove))
		if not job_accepted: return not_done[i:]
		else: print(f,'ppl job accepted')
		time.sleep(0.1)
	if i < len(not_done) -1: not_done[i+1:]
	return []

def handle_pdf(tm, pdf_dir, ppl_dir, lexicon):
	''' Transform any ppl file (not yet processed) to pdf files (np array with word pdf).
	tm 			thread master
	pdf_dir 	location for pdf files, np array with probs for each word for a specific precontext
	ppl_dir 	location for ppl files (ngram debug -2 output) 
	lexicon 	all words to generate word prob distribution for
	'''
	# check the files in the ppl_dir
	fn = glob.glob(ppl_dir + '*')
	# check whether there are file that are not yet processed
	not_done = [f for f in fn if not check_pdf_done(filename2name(f))]
	not_done = [f for f in not_done if os.stat(f).st_size > 100]
	if len(not_done) == 0: return []
	print('pdf handling files:',' '.join(not_done))
	for i,f in enumerate(not_done):
		name = filename2name(f)
		pdf_name = pdf_dir + name + '.pdf'
		print('pdf processing:',f,'saving to:',pdf_name)
		job_accepted = tm.add_thread('pdf',make_pdf,(f,pdf_name, lexicon))
		if not job_accepted: return not_done[i:]
		else: print(f,'pdf job accepted')
	if i < len(not_done) -1: not_done[i+1:]
	return []

def wait_until_ready(f):
	old_file_size = os.stat(f).st_size
	n = 0
	while 1:
		if os.path.isfile('FINISHED_PPL/' + filename2name(f)): return time.time()
		file_size = os.stat(f).st_size
		if file_size == old_file_size and file_size > 100*10**6:
			n += 1
		old_file_size = file_size
		time.sleep(9)
		if n > 9: break
	return time.time()
		
		

def make_pdf(f,pdf_name, lexicon):
	'''Create an np array with word prob for each word in lexicon given specific precontext.
	f 			filename of the ppl file
	pdf_name 	filename of the word pdf numpy array
	lexicon 	all words to generate word prob distribution for
	'''
	os.system('touch DONE_PDF/'+ filename2name(pdf_name))
	print('starting at:',wait_until_ready(f),'creating pdf file with',f)
	ppl = open(f,encoding = 'utf8').read().split('\n\n')
	output = []
	for i, l in enumerate(ppl[:-1]):
		# order and word should correspond to the lexicon.
		if lexicon[i] != l.split('p( ')[-1].split(' | ')[0]: 
			print('words should equal:',lexicon[i],l.split('p( ')[-1])
			return
		output.append(float(l.split(' sentences, ')[0].split(' ]')[-2].split('[ ')[-1]))
	# number of words in pdf should correspond to n words in lexicon
	if len(output) != len(lexicon):  
		print('problems',f,pdf_name,len(output),len(lexicon))
		return
	np.save(pdf_name,np.array(output))
	# some file are kept to check everything worked as expected
	if not check_in_keep(f): 
		with open(f,'w') as fout: fout.write('')
	print(pdf_name,'word pdf is complete',time.time())
		

def make_ppl(f,ppl_name,lm_name, remove = True):
	'''Compute logprobs on lexicon text with ngram call.
	f 			filename of the lexicon text
	ppl_name 	filename of the perplexity file (ngram output)
	lm_name 	srilm trained lm
	remove 		whether to remove most lexicon text file or keep everything
	'''
	os.system('touch DONE_PPL/'+ filename2name(ppl_name))
	command = 'ngram -order 4 -no-sos -no-eos -lm ' + lm_name + ' -debug 2 -ppl ' + f + ' > ' + ppl_name
	print('command:',command)
	os.system(command)
	# some file are kept to check everything worked as expected
	# 98 % of lexicon text and ppl file are removed, if lexicon text is kept, corresponding ppl also
	if remove and random.random() > .02: 
		with open(f,'w') as fout: fout.write('')
	else: add_to_keep(f)
	if not remove:print('force added:',f,'to keep files')
	os.system('touch FINISHED_PPL/'+ filename2name(ppl_name))
	print(ppl_name,'ngram is complete',time.time())


def make_lexicon_text(sentence,lexicon,lt_dir):
	'''Makes a text file for a precontext prepended to each word in the lexicon.
	sentence 	sentence (string of words)
	lexicon 	all words to generate word prob distribution for
	lt_dir 		location for lexicon text files
	'''
	lexicon_texts, precontexts = sentence2lexicon_text(sentence,lexicon)
	if lexicon_texts ==[1]:
		print(sentence,'only contains 1 word, nothing to be done')
		return
	for i,pc in enumerate(precontexts):
		if pc == None: 
			print('first word in sentence, nothing to be done')
			continue
		name = pc.replace(' ','_')
		lt_name = lt_dir + name + '.lt'
		if check_lt_done(filename2name(lt_name)):
			print(name,'file for precontext already exists, nothing to be done')
			continue
		save_lexicon_text(lt_name,lexicon_texts[i][1])

def make_file(name):
	with open(name,'w'): pass


def check_lt_done(lt_name):
	'''check whether this file needs to be processed.'''
	done = [filename2name(f) for f in glob.glob('DONE_LT/*')]
	return lt_name in done
	
def check_ppl_done(ppl_name):
	'''check whether this file needs to be processed.'''
	done = [filename2name(f) for f in glob.glob('DONE_PPL/*')]
	return ppl_name in done

def check_pdf_done(pdf_name):
	'''check whether this file needs to be processed.'''
	done = [filename2name(f) for f in glob.glob('DONE_PDF/*')]
	return pdf_name in done

def check_in_keep(f):
	'''Check whether to keep this file, a subset of lt and ppl files are kept to check.'''
	name = filename2name(f)
	keep_names = [filename2name(f) for f in glob.glob('KEEP/*')]
	return name in keep_names

def add_to_keep(f):
	'''Add a file to the keep list.'''
	name = filename2name(f)
	os.system('touch KEEP/'+name)
	

def filename2name(f):
	'''Extract name from file name.'''
	return f.split('/')[-1].split('.')[0]

class thread_master():
	'''Hold all threads for each stage of processing.'''
	def __init__(self,max_nthreads = 10):
		self.max_nthreads = max_nthreads 
		self.lt_threads = []
		self.ppl_threads = []
		self.pdf_threads = []
		self.set_nthreads()

	def __repr__(self):
		self.check_threads()
		return 'thread_master\tlt: '+str(self.lt)+'\tppl: '+str(self.ppl)+'\tpdf: '+str(self.pdf)

	def __str__(self):
		self.check_threads()
		m = 'max nthreads:\t' + str(self.max_nthreads) + '\n'
		m += 'lt:\t\t' + str(self.lt) + '\n' 
		m += 'ppl:\t\t' + str(self.ppl) + '\n'
		m += 'pdf:\t\t' + str(self.pdf) 
		return m

	def thread_available(self,name):
		self.check_threads()
		return getattr(self,name)< self.max_nthreads

	def check_threads(self):
		'''Check whether threads can be removed from list, because the process is finished.'''
		self.lt_threads = check_threads(self.lt_threads)
		self.ppl_threads = check_threads(self.ppl_threads)
		self.pdf_threads = check_threads(self.pdf_threads)
		self.set_nthreads()

	def set_nthreads(self):
		'''Set the number of active threads.'''
		for n in 'lt','ppl','pdf':
			setattr(self,n,len(getattr(self,n+'_threads')))

	def add_thread(self,name, function, args):
		'''Add a thread to a specific pool if this does not overshoot max_nthreads.'''
		self.check_threads()
		thread_list = getattr(self,name+'_threads')
		if len(thread_list) >= self.max_nthreads: return False
		thread_list.append(threading.Thread(target=function,args=args))
		thread_list[-1].start()
		return True
		
		

def check_threads(threads):
	'''Checks whether a thread is still active.'''
	output = []
	for thread in threads:
		if thread.is_alive(): output.append(thread)
	return output


def make_lexicon(lm_name = 'cow_clean10.lm', cum_prob_threshold = .9, overwrite = False):
	filename = 'lexicon_'+lm_name.split('.')[0] + '_s' + str(int(cum_prob_threshold*100))
	if os.path.isfile(filename) and not overwrite:
		print('doing nothing lexicon already exists, use overwrite to make again.')
		return
	print('opening file')
	lm = open(lm_name,encoding = 'utf8').read().split('\n')
	ngram = [l.split('\t') for l in lm]
	print('extracting unigrams')
	unigram= [l for l in ngram if len(l) in [2,3] and type(l) == list and ' ' not in l[1]]
	probs = [[float(g[0]),g[1]] for g in unigram]
	probs.sort(key=lambda x: x[0],reverse=True)
	cum_prob = 0
	print('computing probabilities and cumulative probs')
	for line in probs:
		line.append(10**line[0])
		cum_prob += line[2]
		line.append(cum_prob)
	print('extracting lexicon')
	lexicon = [w[1] for w in probs if w[-1] < cum_prob_threshold]
	print('nwords in lexicon:',len(lexicon),'cum_prob_threshold',cum_prob_threshold)
	print('saving lexicon:',filename)
	with open(filename,'w') as fout: fout.write('\n'.join(lexicon))
		
