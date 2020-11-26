from .count_words import AllWordCounts,WordInfos
import numpy as np
from matplotlib import pyplot as plt
plt.ion()

class Plotter:
	def __init__(self):
		self.wis = WordInfos()
		self.awc = AllWordCounts()
		self.wis.load()
		self.awc.load()
		self._make_xy()

	def _make_xy(self):
		self.xy = {}
		for word in self.wis.dict.keys():
			self.xy[word] = self._make_word_xy(word)
		self.xy['all'] = self._make_word_xy()
		self._normalize()

	def _normalize(self):
		nd = self.xy['all']
		for word in self.wis.dict.keys():
			self.xy[word+'_normalized'] = {}
			for t in 'year,month,decade'.split(','):
				normalizer = np.array(self.xy['all'][t][-1])/10**6
				dates, values = self.xy[word][t]
				ovalues=[]
				for date,value in zip(dates,values):
					index= nd[t][0].index(date)
					normalizer = nd[t][1][index] / 10**6 
					ovalues.append(value/normalizer+1)
				self.xy[word+'_normalized'][t] = dates,ovalues
				
	def _make_word_xy(self,word = None):
		d = {}
		if word == None: wd = self.awc.dict
		else: wd = self.wis.dict[word]
		for period in wd.keys():
			dates = sorted(wd[period].keys())
			xy =[date for date in dates],[wd[period][date] for date in dates] 
			d[period] = xy
		return d

	def plot_word_bar(self,word):
		plt.clf()
		x,y = self.xy[word]['decade']
		plt.bar(x,y,width=9.8,color = 'lightgrey')
		plt.grid()
		x,y = self.xy[word]['year']
		plt.bar(x,y,width=0.8,color = 'black',align='edge')
		plt.title(word)

	def plot_word_bar_all(self,normalize = False):
		plt.clf()
		fig,axs = plt.subplots(4,4)
		i,j = 0,0
		for word in sorted(list(self.wis.dict.keys())):
			if normalize: 
				w = word +'_normalized'
				ymax = 10
			else: 
				w = word
				ymax = 1000
			# if not normalize: axs[i,j].set_yscale('log')
			axs[i,j].set_yscale('log')
			axs[i,j].set_ylim((0,ymax))
			axs[i,j].set_xlim((1945,2000))
			x,y = self.xy[w]['decade']
			if x == y == []: x,y = [1960],[0.1]
			axs[i,j].bar(x,y,width=9.8,color = 'lightgrey')
			x,y = self.xy[w]['year']
			if x == y == []: x,y = [1960],[0.1]
			axs[i,j].bar(x,y,width=0.8,color = 'black',align='edge')
			x,y = self.xy[word]['decade']
			count = str(sum(y)) if sum(y) > 0.9 else '0'
			leg = axs[i,j].legend([word + ' ' + count])
			for item in leg.legendHandles:
				item.set_visible(False)
			axs[i,j].grid()
			i +=1
			if i>0 and i % 4 == 0:
				if j == 3:
					fig,axs = plt.subplots(4,4)
					i,j = 0,0
				else:
					i = 0
					j += 1
