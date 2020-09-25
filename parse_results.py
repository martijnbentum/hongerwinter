import html
from lxml import etree
from datetime import datetime
import os
import requests
import scheduler
import sys
import time

def get_subjects(paper):
	'''retrieves all subject categories of a newspaper.'''
	xml = make_xml(paper)
	articles = get_articles(xml)
	return list(set([article.getchildren()[0].text for article in articles]))

def get_titles(paper, d = None):
	'''retrieves all subject categories of a newspaper.'''
	if type(d) != dict: d = {}
	xml = make_xml(paper)
	articles = get_articles(xml)
	titles= [article.getchildren()[1].text for article in articles]
	for i,title in enumerate(titles):
		if title in d.keys(): d[title] += 1
		else: d[title] =1 
		'''
		if title in d.keys(): 
			d[title][0] += 1
			d[title][1].append(i)
			d[title][2].append(articles[i].getchildren()[4].text.split(':')[-1])
		else: d[title] =[1,[i],[articles[i].getchildren()[4].text.split(':')[-1]]]
		'''
	return d

def fast_forward(fin,start):
	'''scans to the start index of the results file.'''
	for i,line in enumerate(fin):
		if i == start -1:break
	print('starting file at index: ',start)
	return fin

def next_line(fin):
	'''retrieves the next line of the results file, this contains the metadata of a single newspaper.'''
	next(fin)


def make_xml(line):
	'''create xml object from a single line of the results file, this corresponds to the metadata of a single newspaper.'''
	return etree.fromstring(line.replace('xsi:',''))


# info functions
def make_info(xml,tags,info):
	for tag in tags:
		for cc in xml.getchildren():
			if tag in cc.tag: 
				if tag == 'identifier' and 'resolver' in cc.text: setattr(info,'link',cc.text)
				else: setattr(info,tag,cc.text)
				if not hasattr(info,tag):setattr(info,tag,False)
	return info

def get_paper_info(xml):
	'''retrieves title identification info for a newspaper.
	also sets the link to the delpher website and the distribution of the newspaper national / regional
	'''
	info = type('info',(),{})
	for c in xml.getiterator():
		if 'dcx' in c.tag and len(c.getchildren()) > 12 and 'title' in c.getchildren()[0].tag:
			break
	info = make_info(c,'title,identifier,spatial,language,date'.split(','),info)
	return info
	
def get_article_info(article_xml):
	'''retrivies ocr link, subject of the article.'''
	info = type('info',(),{})
	info = make_info(article_xml,'title,subject,identifier'.split(','),info)
	info.page = article_xml.getparent().getparent().getparent().attrib.values()[0].split(':')[-2].replace('p','')
	return info
# end info function ---


class Info:
	'''general info class'''
	def _set_info(self):
		for tag in self.tags:
			setattr(self,tag,getattr(self.info,tag))

	def __repr__(self):
		return self.title

	def to_xml(self,goal=None):
		if goal == None: self.xml = etree.Element(self.name)
		else: self.xml = etree.SubElement(goal,self.name)
		for tag in self.tags: 
			value = getattr(self,tag)
			e = etree.SubElement(self.xml,tag)
			e.text =str(value)
		
	def xml2string(self):
		if not hasattr(self,'xml'): self.to_xml()
		return etree.tostring(self.xml, encoding = 'utf8',pretty_print=True).decode()

	def print_xml(self):
		print(self.xml2string())

class PaperInfo(Info):
	'''paper information holder'''
	def __init__(self,xml):
		self.info = get_paper_info(xml)
		self.tags ='title,identifier,spatial,language,date,link'.split(',')
		self.name = 'paper_info'
		self._set_info()
		
	def __str__(self):
		return self.title + '\n' + self.date + '\n' + self.spatial

	def add_info(self,narticles, nwords, nerrors,nexcluded_articles,excluded_articles_id):
		self.narticles = narticles
		self.nwords = nwords
		self.nerrors = nerrors
		self.excluded_articles_id = excluded_articles_id
		self.nexcluded_articles = nexcluded_articles
		self.tags.extend(['nwords','narticles','nerrors','nexcluded_articles','excluded_articles_id'])

class Article(Info):
	'''article information holder'''
	def __init__(self,article_xml):
		self.info = get_article_info(article_xml)
		self.tags ='title,subject,link,page'.split(',')
		self.name = 'article'
		self._set_info()

	def __str__(self):
		return self.__repr__()

	def get_text(self):
		if hasattr(self,'text'):return self.text
		self.error,self.text = False,False
		self.tags.extend(['text','error'])
		try:self.text = requests.get(self.link+':ocr',allow_redirects=True).content.decode()
		except:self.error = 'cannot return ocr file: '+str(sys.exc_info())
		else:
			if 'No rule found for urn' in self.text:self.error ='urn'
			if 'The resource you are looking for might have been removed' in self.text:self.error ='removed'
			if '<html><head><title>Error</title></head><body>Not enough rights to view digital object</body></html>' in self.text:
				self.error='no rights'
			if self.error: self.text = False
			else: 
				self.text = html.unescape(self.text)
				self.text ='\n'.join(self.text.replace('</p>','').replace('\r\n','\n').replace('</text>','').split('<p>')[1:])
		return self.text

	def get_nwords(self):
		if not hasattr(self,'text'): self.get_text()
		if not self.text: self.nwords = 0
		else: self.nwords = len(self.text.split(' '))

		
	
		
class Paper():
	def __init__(self,line):
		xml = make_xml(line)
		self.paper_info = PaperInfo(xml)
		articles = get_articles(xml)
		self.articles = [Article(article) for article in articles]
		self._exclude_articles()
		self.narticles = len(self.articles)
		self.text_loaded = False
		self.error = False
		
	def __repr__(self):
		return self.paper_info.__str__()

	def __str__(self):
		m = self.__repr__()+'\n'
		m += 'narticles\t'+str(self.narticles)
		return m

	def _exclude_articles(self):
		r,a = [],[]
		for article in self.articles:
			if article.subject in ['advertentie','familiebericht']:
				r.append(article)
			else: a.append(article)
		self.excluded_articles_id = ','.join([a.link.split(':')[-1] for a in r])
		self.nexcluded_articles = len(r)
		self.articles = a

	def get_text(self):
		self.nwords = 0
		self.nerrors = 0
		for article in self.articles:
			article.get_nwords()
			if article.error == 'no rights': 
				self.error =True
				break
			self.nwords += article.nwords
			if article.error: self.error += 1
		self.text_loaded = True
		

	def to_xml(self):
		if not self.text_loaded: self.get_text()
		self.paper_info.add_info(self.narticles, self.nwords, self.nerrors,self.nexcluded_articles,self.excluded_articles_id)
		self.xml = etree.Element('paper')
		self.paper_info.to_xml(self.xml)
		if not self.error:
			for article in self.articles:
				article.to_xml(self.xml)
	 
	def xml2string(self):
		if not hasattr(self,'xml'): self.to_xml()
		return etree.tostring(self.xml, encoding = 'utf8',pretty_print=True).decode()

	def print_xml(self):
		print(self.xml2string())

		


def get_articles(xml):
	'''get metadata for all articles of a single newspaper.'''
	o = []
	ids,dup = [],[]
	for c in xml.getiterator():
		if 'dcx' in c.tag and len(c.getchildren()) == 6 and 'subject' in c.getchildren()[0].tag:
			i = c.getchildren()[4].text.split(':')[-1]
			if i not in ids:
				# ensure no duplicate articles
				o.append(c)
				ids.append(i)
			else: dup.append(i)
	for item in dup:
		# ensure that every article is in the set
		assert item in ids
	return o

def get_index(prepend):
	if not os.path.isfile(prepend+'index'):
		f = open(prepend+'index','w')
		f.close()
	with open(prepend+'index') as findex:
		temp =findex.read().split('\n')
		if len(temp) > 1:
			index = temp[-2].split('\t')[-1]
		else: index = 0
	return int(index)

def get_time():
	return datetime.now().strftime('%m-%d %H:%M')


def write_index(index,prepend):
	with open(prepend+'index','a') as fout:
		fout.write(get_time() + '\t' + str(index)+'\n')
	return index
	

def handle_file(f,prepend):
	fin = open(f)
	index = get_index(prepend)
	if index > 0: fast_forward(fin,index)
	print('starting at line: ',index)
	narticles, nerrors,nwords = 0,0,0
	years = []
	year_dict = {}
	while True:
		if index % 1000 == 0 or os.path.isfile('stop'): 
			print('saving files')
			for year in year_dict.keys():
				for paper in year_dict[year]:
					with open(prepend + year + '-ocr','a') as fout:
						fout.write(paper.xml2string())
						nerrors += paper.nerrors
						narticles += paper.narticles
						nwords += paper.nwords
			index = write_index(index,prepend)
			print('parsed years:',list(set(years)))
			print('downloaded years:',list(year_dict.keys()))
			print('downloaded:\nArticles:',str(narticles))
			print('nerrors:',str(nerrors))	
			print('nwords:',str(nwords))
			print('starting line ',index,get_time())
			if narticles> 0: wait_until_leisuretime()
			years = []
			year_dict = {}
		if os.path.isfile('stop'): 
			print('found stop file: halting operation',index)
			break
		try:line = next(fin)
		except: break
		paper = Paper(line)
		year = paper.paper_info.date.split('-')[0]
		years.append(year)
		if int(year) < 1945: 
			index += 1
			continue
		try:paper.to_xml()
		except: 
			error = str(i) + ' ' + sys.exc_info()
			with open(prepend + 'error','a') as fout:
				fout.write(error + '\n')
		else:
			if year in year_dict.keys():year_dict[year].append(paper)
			else: year_dict[year] = [paper]
		index +=1

def handle_kranten():
	print('parsing kranten_results.txt')
	handle_file('kranten_results.txt',prepend ='kranten-')

def handle_ddd():
	print('parsing (ddd) results.txt')
	handle_file('/vol/tensusers/mbentum/hongerwinter/oai2linerec/results.txt',prepend='ddd-')

def seconds2time(s):
	hours = z(s/3600)
	minutes = z(s%3600/60)
	seconds = z(s%3600%60)
	return (':').join([hours,minutes,seconds])

def z(t):
	t = int(t)
	if len(str(t)) == 1: return '0'+str(t)
	return str(t)

def wait_until_leisuretime():
	while True:
		if scheduler.is_leisuretime(): break
		seconds = scheduler.time2('leisuretime')
		print(get_time())
		print('waiting for leisure time', seconds2time(seconds),)
		time.sleep(60)



'''
old

def handle_paper(paper):
	xml = make_xml(paper)
	paper_info = get_paper_info(xml)
	articles = get_articles(xml)
	articles_info = [get_article_info(article) for article in articles]

def handle_line(line):
	xml = make_xml(line)
	paper_info = get_paper_info(xml)
	date = get_date(xml)
	articles = get_articles(xml)
	links = [article2ocrlink(a) for a in articles]
	return paper_info,articles,links,date

def format_line(line):
	pi,articles,links,date = handle_line(line)
	if len(links) == 0: return False, False
	main = ':'.join(links[0].split(':')[:-1])
	article_links = ','.join([l.split(':')[-1] for l in links])
	row = '\t'.join([date,main,article_links])
	year = date.split('-')[0] if row else False
	return row, year

def handle_file(f='kranten_results.txt',prepend = 'kranten-'):
	fin = open(f)
	index = get_index()
	if index > 0: fast_forward(fin,index)
	print('starting at line: ',index)
	year_dict = {}
	end = False
	while True:
		if index % 1000 == 0 or os.path.isfile('stop') or end: 
			print('saving lines for years:',','.join(year_dict.keys()))
			for year in year_dict.keys():
				append_rows(year_dict[year],prepend+year)
			year_dict = {}
			index = write_index(index)
			print('done')
			print('starting line ',index,get_time())
		if os.path.isfile('stop'): 
			print('found stop file: halting operation',index)
			break
		try:line = next(fin)
		except:
			end = True
			continue
		row, year = format_line(line)
		if not row or int(year) < 1900:
			index +=1
			continue
		if year in year_dict.keys():
			year_dict[year].append(row)
		else: year_dict[year] = [row]
		index +=1
		# append_row(row,prepend+year)
		# index = write_index(index)

	
def append_row(row,f):
	with open(f,'a') as fout:
		fout.write(row + '\n')

def append_rows(rows,f):
	with open(f,'a') as fout:
		fout.write('\n'.join(rows) + '\n')

def article2ocrlink(a):
	#get the ocrlink for a specific article.
	return a.getchildren()[4].text

def get_date(xml):
	#get the dat of a specific newspaper.
	for c in xml.getiterator():
		if 'date' in c.tag: return c.text
	return False

'''	
