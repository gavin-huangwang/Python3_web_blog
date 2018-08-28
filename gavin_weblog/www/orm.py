# -*- coding:utf-8 -*- /
import asyncio, logging
import aiomysql


#��¼sql����
def log(sql,args = ()):
	logging.info('SQL:%s' % sql)

#����ȫ�����ӳأ�**kw �ؼ��ֲ����������ڴ���host port user password db�ȵ����ݿ����Ӳ���
async def create_pool(loop,**kw):
	#������־
	logging.info('crareate databases connection pool')
	global __pool		#ȫ�ֱ���
	__pool = await aiomysql.create_pool(
	host = kw.get('host','localhost'),
	port = kw.get('port','3306'),
	user = kw['user'],
	password = kw['password'],
	db = kw['db'],
	charset = kw.get('charset','utf8'),		#�������ݿ���룬Ĭ��utf8
	autocommit = kw.get('autocommit',True),		#�����Զ��ύ����Ĭ�ϴ�
	maxsize = kw.get('maxsize',10),		 #���������������Ĭ��10
	minsize = kw.get('minsize',1),		 #������С��������Ĭ��1
	loop=loop,		#��Ҫ����һ���¼�ѭ��ʵ���������ر�������Ĭ��ʹ��asyncio.get_event_loop()
	)
		
#ʵ��SQL��䣺SELECT����������ֱ�ΪSQL��䡢SQL�����ռλ����Ӧ�Ĳ����������ؼ�¼���� 
async def select(sql,args,size=None):
	log(sql,args)
	global __pool
	async with __pool.get() as conn:		#�����ӳ��л�ȡһ�����ӣ�ʹ������Զ��ͷ�		
		async with cunn.cursor(aiomysql.DictCursor) as cur:		#����һ���α꣬������dict��ɵ�list��ʹ������Զ��ͷ�
			await cur.execute(sql.replace('?', '%s'), args or ()) #ִ��SQL��mysql��ռλ����%s����pythonһ����Ϊ��coding�ı���������SQL��ռλ����дSQL��䣬���ִ��ʱ��ת������
			if size:
				rs = await cur.fetchmany(size)		#ֻ��ȡsize����¼
			else:
				rs = await cur.fetchall()		#���ص�rs��һ��list��ÿ��Ԫ����һ��dict��һ��dict����һ�м�¼,json
			#await cur.close()
		logging.info('rows returned:%s' % len(rs))		# �ж��ٸ�dict���Ƕ��м�¼
		return rs

#mysql���룬ɾ�������·���������һ������ʵ������Ϊ��ͨ��ormʵ�������ݿ��������������������ʵ�ʵ���ɾ�Ĳ���������ͨ���෽������������ʵ�֣�������ֻ��Ҫ��ע������Ӱ������˿���ģ�廯
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
				await conn.commit()		#�ύ����
		except BaseException as e:
			if not autocommit:
				await conn.rollback()		#�ع�����ǰ������Э��
			raise
		return affect

#��������������ռλ���ַ�������������sq���
def create_args_string(num):
	L = []
	for n in range(num):	#sql�ã���ռλ����num�Ǽ����м���ռλ��
		L.append('?')
	return ', '.join(L)
	
#' ����һ���������͵Ļ��࣬�������� ������ORM�� ��Ӧ ���ݿ���������� ���� '
class Field(object):
	def __init__(self,name,column_type,primary_key,default):
		self.name=name
		self.column_type=column_type
		self.primary_key=primary_key
		self.default=default
		
	def __str__(self):
		return '<%s,%s:%s>' % (self.__class__.__name__,self.column_type,self.name)

#�����ַ���ΪField������
class StringField(Field):
	def __init__(self,name=None,primary_key=False,default=None,ddl='varchar(100)'):
		super().__init__(name,ddl,primary_key,default)

#����������ΪField������
class IntegerField(Field):
	def __init__(self,name=None,primary_key=False,default=0):
		super().__init__(name,'bigint',primary_key,default)

#���岼����ΪField������
class BooleanField(Field):
	def __init__(self,name=None,default=False):
		super().__init__(name,'boolean',False,default)

#���帡����ΪField������
class FloatField(Field):
	def __init__(self,name=None,primary_key=False,default=0.0):
		super().__init__(name,'real',primary_key,default)

#�����ı���ΪField������
class TextField(Field):
	def __init__(self,name=None,default=None):
		super().__init__(name,'text',False,default)

#ORMԪ�࣬�͸�����ʽ���������Դ����࣬����Model������ͨ��Ԫ�ඨ��ķ�����ɨ��ӳ���ϵ�Ӷ��ӵ���Ӧ���б���ֵ��У�
#ע��Ԫ��ṹ��ԽϹ̶�
class ModelMetaclass(type):
	def __new__(cls,name,bases,attrs):
		#�ų�Model�౾��,�Ӷ�ֻ����Model����
		if name == 'Model':
			return type.__new__(cls,name,bases,attrs)
		#ͨ��__table__����User���л�ȡ����
		tableName = attrs.get('__table__',None) or name
		logging.info('found model: %s (table: %s)' % (name,tableName))
		#��ȡ���б���ֶκ�������
		mappings = dict()	#�����洢�����Ͷ�Ӧ����������
		fields = []		#�������������
		primaryKey = None	#�������أ�Ĭ�ϲ��غ�
		#��ѭ����������atttr�������ϣ����ھ�������
		for k,v in attrs.items():
			#isinstance��type���ƣ����ῼ�Ǽ̳й�ϵ��type(3,int)=isinstance(3,int),���صĶ���True
			if isinstance(v,Field):
				logging.info(' found mapping: %s--%s' % (k,v))
				mappings[k] = v
				if v.primary_key:
					#�ҵ�������
					if primaryKey:
						raise StandardError('Duplicate primary key for field: %s' % k)
					primaryKey = k
				else:
					fields.append(k)
		if not primaryKey:
			raise StandardError('Primary key not found')
		#����������Ϊ�˷�ֹʵ������������һ�³���
		for k in mappings.keys():
			attrs.pop(k)
		escaped_fields = list(map(lambda f: '`%s`' % f, fields))	#���������м�``����ִ�����������''���ַ���Ч����
		#�������Ժ��е�ӳ���ϵ
		#�ڴ�������Կ���������Ƕ�׽ṹ��attrs��ֵ�����ݼ���
		attrs['__mappings__'] = mappings
		attrs['__table__'] = tableName
		#����������
		attrs['__primary_key__'] = primaryKey
		#�������������е�������
		attrs['__fields__'] = fields
		#����Ĭ��select���
		attrs['__select__']	= 'select `%s`, %s from `%s`' % (primaryKey,', '.join(escaped_fields),tableName)
		#����Ĭ��insert���
		attrs['__insert__'] = 'insert into `%s` (%s,`%s`) values (%s)' % (tableName,', '.join(escaped_fields),primaryKey,create_args_string(len(escaped_fields)+1))
		#����Ĭ��update���
		attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName,', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
		#����Ĭ��deleta���
		attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName,primaryKey)
		#���ص�ǰ׼����������Ķ���������֡���̳еĸ��༯�ϡ���ķ������ϣ��������ϴ��봦������ܼ��ϣ�
		return type.__new__(cls,name,bases,attrs)
			
#����һ����Ӧ ���ݿ��������� ��ģ���ࡣͨ���̳У����dict�����Ժ�Ԫ����������ݿ��ӳ���ϵ '
# ��ģ��������������ʱ�����ģ����û���¶���__new__()��������˻�ʹ�ø���ModelMetaclass��__new__()�����������࣬�Ӷ�ʵ��ORM
class Model(dict,metaclass=ModelMetaclass):
	def __init__(self,**kw):
		super(Model,self).__init__(**kw)
		
	#���ԵĶ�̬�󶨺ͻ�ȡ	
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
			field = self.__mappings__[key]	#��ȡ���Զ�Ӧ���е���������Ĭ��ֵ
			if field.defalt is not None:
				value = field.default() if callable(field.default) else field.default
				logging.debug('using default value for %s: %s' % (key,str(value)))
				setattr(self,key,value)
		return value
	
	@classmethod#����෽������Ӧ���Ĭ�ϲ���������ͨ��where limit���ò�������
	async def findAll(cls,where=None,args=None,**kw):
		sql = [cls.__select__]	#���б�洢select���
		if where:
			sql.append('where')
			sql.append(where)
		if args is None:
			args = []
		#�Բ�ѯ�������
		orderBy = kw.get('orderBy',None)	
		if orderBy:
			sql.append('order by')
			sql.append(orderBy)
		#��ȡ��ѯ���
		limit = kw.get('limit',None)
		if limit is not None:
			sql.append('limit')
			if isinstance(limit,int):
				sql.append('?')		#?�ᱻlimit�滻
			elif isinstance(limit,tuple) and len(limit) == 2:		#�Թ���һ����¼���ڶ�����ʼ��ȡ
				sql.append('?,?')
				args.extend(limit)		#��limit�ϲ���args�б��ĩβ
			else:
				raise ValeError('Invalid limit value: %s' % str(limit))
		#������º��select��䣬��ִ�У����ز�ѯ�����
		rs = await select(' '.join(sql),args)
		return [cls(**r) for r in rs]
	
	@classmethod#��ӷ����������ض��У�ͨ��where���ù�������
	async def findNumber(cls,selectField,where=None,args=None):
		# _num_��SQL��һ���ֶα����÷���AS�ؼ��ֿ���ʡ��
		sql = ['select %s _num_ from `%s`' % (selectField,cls.__table__)]
		if where:
			sql.append('where')
			sql.append(where)
		rs = await select(' '.join(sql),args,1)
		if len(rs) == 0:
			return None
		return rs[0]['_num_']
	
	@classmethod
	#ͨ��������ѯһ������
	async def find(cls,pk):
		rs = await select('%s where `%s`=?' % (cls.__select__,cls.__primary_key__),[pk],1)
		if len(rs) == 0:
			return None
		return cls(**rs[0])
	
	#���ʵ��������ӳ������¼
	async def save(self):
		#map������ṩ�ĺ�����ָ��������ӳ����map(x**2,[1,2,3,4])=[1,4,9,16]
		args = list(map(self.getValueOrDefault,self.__fields__))	#��������ֵ
		args.append(self.getValueOrDefault(self.__primary_key__))	#������ֵ
		rows = await execute(self.__insert__,args)					#ִ�в��뷽��
		if rows != 1:
			logging.warm('failed to insert record: affected rows: %s' % rows)

	#���ʵ��������ӳ����¼�¼
	async def update(self):
		args = list(map(self.getValue,self.__fields__))				#��������ֵ
		args.append(self.getValue(self.__primary_key__))			#������ֵ
		rows = await execute(self.__update__,args)				
		if rows != 1:
			logging.warm('failed to update by primary key: affected rows: %s' % rows)

	#���ʵ��������ӳ��ɾ����¼
	async def remove(self):
		args = [self.getValue(self.__primary_key__)]	#��������ֵɾ��
		rows = await execute(self.__delete__,args)				
		if rows != 1:
			logging.warm('failed to remove by primary key: affected rows: %s' % rows)


#ORM����ӳ���ϵ��ָͨ����orm���е����Ժͱ��е��н��й�����ͨ��������������ʵ�����ݿ���еľ����еĲ���
#ע��orm��ʵ���߼���orm��������Model,����̳�Ԫ��/��ͨ��Ԫ�ഴ���ģ����orm���е�������Ԫ�����
#class User(Model):
#	__table__ = 'users'
#	
#	id = IntegerField(primary_key=True)
#	name = StringField()
#	
#	user = User(id=123, name='Michael')
#	yield from user.save()
