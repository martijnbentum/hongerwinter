import glob
import os
import parse_results as pr
import requests
import scheduler
import sys
import time

def get_ocr(url):
	return requests.get(url+':ocr',allow_redirects=True).content.decode()

def line2urls(line):
	date, preprend, article_ids = line.split('\t')
	return date, [preprend+ ':'+article_id for article_id in article_ids.split(',')]


def handle_all():
	fn = glob.glob('kranten*')
	nfn = len(fn)
	for i,f in enumerate(fn):
		if f == 'kranten_results.txt':continue
		print('processing file:',f)
		output = []
		if finished_files_ocr(f): 
			print('already processed:',f)
			continue
		filename = 'ocr-'+f
		fout = open(filename,'w')
		fout.close()
		o = handle_file(f)
		no = len(o)
		j = 0
		fast_forward = False
		for date, url in o:
			if fast_forward:
				if paper_id in url: continue
				else: 
					print('skipped articles in:',paper_id,'now starting:',url)
					fast_forward = False
			if j > 300: wait_until_leisuretime()
			try: ocr = get_ocr(url)
			except:
				error = 'cannot return ocr file: '+str(sys.exc_info())
				with open('errors-ocr-kranten','a') as fout:
					fout.write('\t'.join([date,url,error]) +'\n')
				print('cannot read ocr file',pr.get_time())
				continue
			error, paper_id = check_ocr(f,date,ocr,url)
			if not error: output.append(date+'\t'+ocr)
			elif error == 'no rights':
				fast_forward = True
				continue
			if len(output) >= 300:
				print('handling file number:',i,'of', nfn,pr.get_time())
				print('handling article number:',j,'of',no)
				print('writing data for: ',filename)
				with open(filename,'a') as fout:
					fout.write('\n'.join(output)+'\n')
				output = []
			j+=1
		with open('finished-files-ocr-kranten','a') as fout:
			fout.write(f +'\n')
		

		
		

def handle_file(f):
	t = open(f).read().split('\n')
	o = []
	for line in t:
		if not line: continue
		date, urls = line2urls(line)
		o.extend([[date, url] for url in urls])
	return o

def check_ocr(f,date,ocr,url):
	error = False
	if 'No rule found for urn' in ocr:error ='urn'
	if 'The resource you are looking for might have been removed' in ocr:error ='removed'
	if '<html><head><title>Error</title></head><body>Not enough rights to view digital object</body></html>' in ocr:
		error='no rights'
	if error:
		if error !='no rights':print('found an error for:',f,date,url,error)
		with open('errors-ocr-kranten','a') as fout:
			fout.write('\t'.join([date,url,error]) +'\n')
		if error == 'no rights': return error,url.split(':')[-3]
		return True,None
	return False,None

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
		print(pr.get_time())
		print('waiting for leisure time', seconds2time(seconds),)
		time.sleep(60)


def finished_files_ocr(f):
	return f in  open('finished-files-ocr-kranten').read().split('\n')

