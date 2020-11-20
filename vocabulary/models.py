from django.db import models
from utils.model_util import info


class Word(models.Model,info):
	word = models.CharField(max_length=100)
	count = models.PositiveIntegerField(null=True,blank=True)
	word_class = models.CharField(max_length=300)
	pos = models.CharField(max_length=100)
	national = models.BooleanField(default = False)
	regional= models.BooleanField(default=False)
	colonial= models.BooleanField(default=False)

	def __str__(self):
		return self.word

	class Meta:
		unique_together = [['word','pos']]


class Paper(models.Model,info):
	title= models.CharField(max_length=400)
	location= models.CharField(max_length=400)
	location_category = models.CharField(max_length=50,default = '')
	language= models.CharField(max_length=400)
	ids= models.CharField(max_length=400)
	link = models.CharField(max_length=400,unique=True)
	narticles= models.PositiveIntegerField(null=True,blank=True)
	nexcluded_articles = models.PositiveIntegerField(null=True,blank=True)
	excluded_article_ids = models.TextField(default='')
	nerrors = models.PositiveIntegerField(null=True,blank=True)
	nword_types = models.PositiveIntegerField(null=True,blank=True)
	nword_tokens = models.PositiveIntegerField(null=True,blank=True)
	date = models.DateField()

	def __str__(self):
		return self.title

class Article(models.Model,info):
	dargs = {'on_delete':models.SET_NULL,'blank':True,'null':True} 
	paper = models.ForeignKey(Paper,**dargs)
	title= models.CharField(max_length=400)
	link = models.CharField(max_length=400,unique=True)
	text = models.TextField(default = '')
	subject = models.CharField(max_length=90)
	nword_types = models.PositiveIntegerField(null=True,blank=True)
	nword_tokens = models.PositiveIntegerField(null=True,blank=True)
	page = models.PositiveIntegerField(null=True,blank=True)
	date = models.DateField()

	def __str__(self):
		return self.title
	

class WordArticleRelation(models.Model,info):
	word = models.ForeignKey(Word,on_delete=models.CASCADE)
	article = models.ForeignKey(Article,on_delete=models.CASCADE)
	count = models.PositiveIntegerField()
	date = models.DateField(default = None)
	location_category = models.CharField(max_length=50,default = '')
	hongerwinter = models.BooleanField(default=False)
	

	def __str__(self):
		m = self.word.word+ ' occurs ' + str(self.count)  
		m += ' times in: '+ self.article.title
		return m
	
	class Meta:
		unique_together = [['word','article']]

