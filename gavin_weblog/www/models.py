# -*- coding:utf-8 -*- 
#user,blog,comment models
from orm import Model,StringField,IntegerField,BooleanField,FloatField,TextField
import time,uuid

def next_id():
	return '%015d%s000' % (int(time.time() * 1000),uuid.uuid4().hex) 

#user`s model
class User(Model):
	__table__ = 'users'		#User类映射mysql库中的user表
	
	id = StringField(primary_key = True,default = next_id,ddl = 'varchar(50)')
	email = StringField(ddl = 'varchar(50)')		#用来作为登录账号
	passwd = StringField(ddl = 'varchar(50)')
	admin = BooleanField()
	name = StringField(ddl = 'varchar(50)')
	image = StringField(ddl = 'varchar(500)')
	created_at = FloatField(default = time.time)
	
#blog`s model
class Blog(Model):
	__table__ = 'blogs'
	
	id = StringField(primary_key = True,default = next_id,ddl = 'varchar(50)')
	user_id = StringField(ddl = 'varchar(50)')
	user_name = StringField(ddl = 'varchar(50)')
	user_image = StringField(ddl = 'varchar(500)')
	name = StringField(ddl = 'varchar(50)')
	summary = StringField(ddl = 'varchar(50)')
	content = TextField()
	created_at = FloatField(default = time.time)

#comment`s model
class Comment(Model):
	__table__ = 'comments'
	
	id = StringField(primary_key = True,default = next_id,ddl = 'varchar(50)')
	blog_id = StringField(ddl = 'varchar(50)')
	user_id = StringField(ddl = 'varchar(50)')
	user_name = StringField(ddl = 'varchar(50)')
	user_image = StringField(ddl = 'varchar(500)')
	content = TextField()
	created_at = FloatField(default = time.time)
