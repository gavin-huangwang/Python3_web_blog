# -*- coding:utf-8 -*- /
import asyncio, logging
import aiomysql


#记录sql操作
def log(sql,args = ()):
	logging.info('SQL:%s' % sql)

#创建全局连接池，**kw 关键字参数集，用于传递host port user password db等的数据库连接参数
async def create_pool(loop,**kw):
	#创建日志
	logging.info('crareate databases connection pool')
	global __pool		#全局变量
	__pool = await aiomysql.create_pool(
	host = kw.get('host','localhost'),
	port = kw.get('port','3306'),
	user = kw['user'],
	password = kw['password'],
	db = kw['db'],
	charset = kw.get('charset','utf8'),		#设置数据库编码，默认utf8
	autocommit = kw.get('autocommit',True),		#设置自动提交事务，默认打开
	maxsize = kw.get('maxsize',10),		 #设置最大连接数，默认10
	minsize = kw.get('minsize',1),		 #设置最小连接数，默认1
	loop=loop,		#需要传递一个事件循环实例，若无特别声明，默认使用asyncio.get_event_loop()
	)
		
#实现SQL语句：SELECT。传入参数分别为SQL语句、SQL语句中占位符对应的参数集、返回记录行数 
async def select(sql,args,size=None):
	log(sql,args)
	global __pool
	async with __pool.get() as conn:		#从连接池中获取一个连接，使用完后自动释放		
		async with cunn.cursor(aiomysql.DictCursor) as cur:		#创建一个游标，返回由dict组成的list，使用完后自动释放
			await cur.execute(sql.replace('?', '%s'), args or ()) #执行SQL，mysql的占位符是%s，和python一样，为了coding的便利，先用SQL的占位符？写SQL语句，最后执行时在转换过来
			if size:
				rs = await cur.fetchmany(size)		#只读取size条记录
			else:
				rs = await cur.fetchall()		#返回的rs是一个list，每个元素是一个dict，一个dict代表一行记录,json
			#await cur.close()
		logging.info('rows returned:%s' % len(rs))		# 有多少个dict就是多行记录
		return rs

#mysql插入，删除，更新方法，可以一个方法实现是因为，通过orm实现了数据库表和行于类对象关联，因此实际的增删改操作都可以通过类方法来操作对象实现，而我们只需要关注操作的影响结果因此可以模板化
async def execute(sql,args,autocommit=True):
	log(sql)
	async with __pool.acquire() as conn:
		if not autocommit:
			await conn.begin()
		try:
			async with conn.cursor(aiomysql.DictCursor) as cur:
				await cur.execute(sql.replace('?','%s'),args)
				affected = cur.rowcount
			if not autocommit:
				await conn.commit()		#提交事务
		except BaseException as e:
			if not autocommit:
				await conn.rollback()		#回滚到当前启动的协程
			raise
		return affect

#按参数个数制作占位符字符串，用于生成sq语句
def create_args_string(num):
	L = []
	for n in range(num):	#sql用？做占位符，num是几即有几个占位符
		L.append('?')
	return ', '.join(L)
	
#' 定义一个数据类型的基类，用于衍生 各种在ORM中 对应 数据库的数据类型 的类 '
class Field(object):
	def __init__(self,name,column_type,primary_key,default):
		self.name=name
		self.column_type=column_type
		self.primary_key=primary_key
		self.default=default
		
	def __str__(self):
		return '<%s,%s:%s>' % (self.__class__.__name__,self.column_type,self.name)

#定义字符类为Field的子类
class StringField(Field):
	def __init__(self,name=None,primary_key=False,default=None,ddl='varchar(100)'):
		super().__init__(name,ddl,primary_key,default)

#定义整数类为Field的子类
class IntegerField(Field):
	def __init__(self,name=None,primary_key=False,default=0):
		super().__init__(name,'bigint',primary_key,default)

#定义布尔类为Field的子类
class BooleanField(Field):
	def __init__(self,name=None,default=False):
		super().__init__(name,'boolean',False,default)

#定义浮点类为Field的子类
class FloatField(Field):
	def __init__(self,name=None,primary_key=False,default=0.0):
		super().__init__(name,'real',primary_key,default)

#定义文本类为Field的子类
class TextField(Field):
	def __init__(self,name=None,default=None):
		super().__init__(name,'text',False,default)

#ORM元类，和父类形式，不过可以创建类，并对Model的子类通过元类定义的方法来扫描映射关系从而加到对应的列表和字典中；
#注意元类结构相对较固定
class ModelMetaclass(type):
	def __new__(cls,name,bases,attrs):
		#排除Model类本身,从而只作用Model子类
		if name == 'Model':
			return type.__new__(cls,name,bases,attrs)
		#通过__table__，从User类中获取表明
		tableName = attrs.get('__table__',None) or name
		logging.info('found model: %s (table: %s)' % (name,tableName))
		#获取所有表的字段和主键名
		mappings = dict()	#用来存储列名和对应的数据类型
		fields = []		#存主键外的列名
		primaryKey = None	#主键排重，默认不重合
		#该循环遍历的是atttr方法集合，看②就能明白
		for k,v in attrs.items():
			#isinstance和type类似，但会考虑继承关系如type(3,int)=isinstance(3,int),返回的都是True
			if isinstance(v,Field):
				logging.info(' found mapping: %s--%s' % (k,v))
				mappings[k] = v
				if v.primary_key:
					#找到主键：
					if primaryKey:
						raise StandardError('Duplicate primary key for field: %s' % k)
					primaryKey = k
				else:
					fields.append(k)
		if not primaryKey:
			raise StandardError('Primary key not found')
		#弹出主键是为了防止实例名和主键名一致出错
		for k in mappings.keys():
			attrs.pop(k)
		escaped_fields = list(map(lambda f: '`%s`' % f, fields))	#给非主键列加``（可执行命令）区别于''（字符串效果）
		#保存属性和列的映射关系
		#②从上面可以看出这是种嵌套结构，attrs的值是数据集合
		attrs['__mappings__'] = mappings
		attrs['__table__'] = tableName
		#主键属性名
		attrs['__primary_key__'] = primaryKey
		#除主键外其他列的属性名
		attrs['__fields__'] = fields
		#构造默认select语句
		attrs['__select__']	= 'select `%s`, %s from `%s`' % (primaryKey,', '.join(escaped_fields),tableName)
		#构造默认insert语句
		attrs['__insert__'] = 'insert into `%s` (%s,`%s`) values (%s)' % (tableName,', '.join(escaped_fields),primaryKey,create_args_string(len(escaped_fields)+1))
		#构造默认update语句
		attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName,', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
		#构造默认deleta语句
		attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName,primaryKey)
		#返回当前准备创建的类的对象、类的名字、类继承的父类集合、类的方法集合（经过以上代码处理过的总集合）
		return type.__new__(cls,name,bases,attrs)
			
#定义一个对应 数据库数据类型 的模板类。通过继承，获得dict的特性和元类的类与数据库的映射关系 '
# 由模板类衍生其他类时，这个模板类没重新定义__new__()方法，因此会使用父类ModelMetaclass的__new__()来生成衍生类，从而实现ORM
class Model(dict,metaclass=ModelMetaclass):
	def __init__(self,**kw):
		super(Model,self).__init__(**kw)
		
	#属性的动态绑定和获取	
	def __getattr__(self,key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(r"'model' object has not attribute '%s'" % key)

	def __setattr__(self,key,value):
		self[key] = value
	
	def getValue(self,key):
		return getattr(self,key,None)
	
	def getValueOrDefault(self,key):
		value = getattr(self,key,None)
		if value is None:
			field = self.__mappings__[key]	#查取属性对应的列的数量类型默认值
			if field.defalt is not None:
				value = field.default() if callable(field.default) else field.default
				logging.debug('using default value for %s: %s' % (key,str(value)))
				setattr(self,key,value)
		return value
	
	@classmethod#添加类方法，对应查表，默认查整个表，可通过where limit设置查找条件
	async def findAll(cls,where=None,args=None,**kw):
		sql = [cls.__select__]	#用列表存储select语句
		if where:
			sql.append('where')
			sql.append(where)
		if args is None:
			args = []
		#对查询结果排序
		orderBy = kw.get('orderBy',None)	
		if orderBy:
			sql.append('order by')
			sql.append(orderBy)
		#截取查询结果
		limit = kw.get('limit',None)
		if limit is not None:
			sql.append('limit')
			if isinstance(limit,int):
				sql.append('?')		#?会被limit替换
			elif isinstance(limit,tuple) and len(limit) == 2:		#略过第一条记录，第二条开始截取
				sql.append('?,?')
				args.extend(limit)		#将limit合并到args列表的末尾
			else:
				raise ValeError('Invalid limit value: %s' % str(limit))
		#构造更新后的select语句，并执行，返回查询结果集
		rs = await select(' '.join(sql),args)
		return [cls(**r) for r in rs]
	
	@classmethod#添加方法，查找特定列，通过where设置过滤条件
	async def findNumber(cls,selectField,where=None,args=None):
		# _num_是SQL的一个字段别名用法，AS关键字可以省略
		sql = ['select %s _num_ from `%s`' % (selectField,cls.__table__)]
		if where:
			sql.append('where')
			sql.append(where)
		rs = await select(' '.join(sql),args,1)
		if len(rs) == 0:
			return None
		return rs[0]['_num_']
	
	@classmethod
	#通过主键查询一条数据
	async def find(cls,pk):
		rs = await select('%s where `%s`=?' % (cls.__select__,cls.__primary_key__),[pk],1)
		if len(rs) == 0:
			return None
		return cls(**rs[0])
	
	#添加实例方法，映射插入记录
	async def save(self):
		#map会根据提供的函数对指定序列做映射如map(x**2,[1,2,3,4])=[1,4,9,16]
		args = list(map(self.getValueOrDefault,self.__fields__))	#非主键列值
		args.append(self.getValueOrDefault(self.__primary_key__))	#主键列值
		rows = await execute(self.__insert__,args)					#执行插入方法
		if rows != 1:
			logging.warm('failed to insert record: affected rows: %s' % rows)

	#添加实例方法，映射更新记录
	async def update(self):
		args = list(map(self.getValue,self.__fields__))				#非主键列值
		args.append(self.getValue(self.__primary_key__))			#主键列值
		rows = await execute(self.__update__,args)				
		if rows != 1:
			logging.warm('failed to update by primary key: affected rows: %s' % rows)

	#添加实例方法，映射删除记录
	async def remove(self):
		args = [self.getValue(self.__primary_key__)]	#根据主键值删除
		rows = await execute(self.__delete__,args)				
		if rows != 1:
			logging.warm('failed to remove by primary key: affected rows: %s' % rows)


#ORM对象映射关系；指通过类orm类中的属性和表中的列进行关联，通过创建类对象就能实现数据库表中的具体行的操作
#注意orm的实现逻辑，orm基础基类Model,基类继承元类/是通过元类创建的，因此orm类中的属性受元类控制
#class User(Model):
#	__table__ = 'users'
#	
#	id = IntegerField(primary_key=True)
#	name = StringField()
#	
#	user = User(id=123, name='Michael')
#	yield from user.save()
