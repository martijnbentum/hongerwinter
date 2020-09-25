from django.db import models
from utils.model_util import info

class base(models.Model):
	pass
	
	def __str__(self):
		if hasattr(self,'name'):
			return self.name
		if hasattr(self,'word'):
			return self.word
		if hasattr(self,'title'):
			return self.title
		raise ValueError('no known attribute to set __str__')



class Word(base,info):
	w_word = models.CharField(max_length=100)
	count = models.PositiveIntegerField(null=True,blank=True)
	word_class = models.CharField(max_length=300)
	pos = models.CharField(max_length=100)

	class Meta:
		unique_together = [['w_word','pos']]


class Paper(base,info):
	title= models.CharField(max_length=400)
	location= models.CharField(max_length=400)
	language= models.CharField(max_length=400)
	ids= models.CharField(max_length=400,unique=True)
	link = models.CharField(max_length=400)
	narticles= models.PositiveIntegerField(null=True,blank=True)
	nexcluded_articles = models.PositiveIntegerField(null=True,blank=True)
	excluded_article_ids = models.TextField(default='')
	nerrors = models.PositiveIntegerField(null=True,blank=True)
	nword_types = models.PositiveIntegerField(null=True,blank=True)
	nword_tokens = models.PositiveIntegerField(null=True,blank=True)
	date = models.DateField()


class Article(base,info):
	dargs = {'on_delete':models.SET_NULL,'blank':True,'null':True} 
	a_paper = models.ForeignKey(Paper,**dargs)
	title= models.CharField(max_length=400)
	link = models.CharField(max_length=400,unique=True)
	text = models.TextField(default = '')
	subject = models.CharField(max_length=90)
	nword_types = models.PositiveIntegerField(null=True,blank=True)
	nword_tokens = models.PositiveIntegerField(null=True,blank=True)
	page = models.PositiveIntegerField(null=True,blank=True)
	date = models.DateField()

	

class WordArticleRelation(base,info):
	war_word = models.ForeignKey(Word,on_delete=models.CASCADE)
	war_article = models.ForeignKey(Article,on_delete=models.CASCADE)
	count = models.PositiveIntegerField()

	@property
	def name(self):
		return self.word+ ' occurs ' + str(self.count) + ' times in: '+ self.text
	
	class Meta:
		unique_together = [['war_word','war_article']]

