# -*- coding: utf-8 -*-
import asyncio,os,inspect,logging,functools
from aiohttp import web
from urllib import parse
from apis import APIError


#①先编写url处理函数，检查url请求类型


#@get装饰器给处理函数绑定url,和http method-GET属性
def get(path):
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args,**kw):
			return func(*args,**kw)
		wrapper.__method__ = 'GET'
		wrapper.__route__ = path
		return wrapper
	return decorator

#@post装饰器给处理函数绑定url,和http method-POST属性
def post(path):
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args,**kw):
			return func(*args,**kw)
		wrapper.__method__ = 'POST'
		wrapper.__route__ = path
		return wrapper
	return decorator


#②请求的参数处理


#检查函数是否有request参数，并返回布尔值，如有在检查该参数是否是函数的最后一个参数，否者抛出异常
def has_reqest_arg(fn):
	params = inspect.signatre(fn).parameters	#获取参数名，参数信息
	found =	False
	for name,param in params.items():
		if name == 'request':
			found = True
			continue	#退出该次循环
		#如果有request参数，且还存在位置参数，抛出异常
		if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
			raise ValueError('request parameter must be the last named parameter in function: %s%s' % (fn.__name__,str(sig)))
	return found
	
#检查函数是否有关键字参数集，返回布尔值
def has_var_kw_arg(fn):
	params = inspect.signatre(fn).parameters	#获取参数名，参数信息
	for name,param in params.items():
		if param.kind == inspect.Parameter.VAR_KEYWORD:
			return True
			
#检查函数是否有命名关键字参数，返回布尔值
def has_named_kw_arg(fn):
	params = inspect.signatre(fn).parameters	#获取参数名，参数信息
	for name,param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY:
			return True
	
#将函数所有命名关键字参数作为元祖返回
def get_named_kw_args(fn):
	args = []
	params = inspect.signatre(fn).parameters	#获取参数名，参数信息]
	for name,param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY:
			args.append(name)
	return tuple(args)

#将函数所有无默认值的关键字参数作为元祖返回
def get_required_kw_args(fn):
	args = []
	params = inspect.signatre(fn).parameters	#获取参数名，参数信息]
	for name,param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
			# param.kind : describes how argument values are bound to the parameter.
			# KEYWORD_ONLY : value must be supplied as keyword argument, which appear after a * or *args
			# param.default : the default value for the parameter,if has no default value,this is set to Parameter.empty
			# Parameter.empty : a special class-level marker to specify absence of default values and annotations
			args.append(name)
	return tuple(args)
	

#③对上方的处理函数进行封装的请求处理器
class RequestHandler(object):
	def __init__(self,app,fn):
		# app : an application instance for registering the fn
		# fn : a request handler with a particular HTTP method and path
		self._app = app
		self._func = fn
		self._has_reqest_arg = has_reqest_arg(fn)	#检查函数是否有request参数，并返回布尔值，如有在检查该参数是否是函数的最后一个参数，否者抛出异常
		self._has_var_kw_arg = has_var_kw_arg(fn)	#检查函数是否有关键字参数集，返回布尔值
		self._has_named_kw_arg = has_named_kw_arg(fn)	#检查函数是否有命名关键字参数，返回布尔值
		self._named_kw_args = get_named_kw_args(fn)		#将函数所有命名关键字参数作为元祖返回
		self._required_kw_args = get_required_kw_args(fn)	#将函数所有无默认值的关键字参数作为元祖返回
	
	#请求处理程序，必须是一个协程，它接受一个请求实例作为它唯一的参数，并返回一个streamresponse派生实例	
	async def __call__(self,request):
		kw = None
		# 当传入的处理函数具有 关键字参数集 或 命名关键字参数 或 request参数
		if self._has_var_kw_arg or self._has_named_kw_arg or self._required_kw_args:
			if request.method == 'POST':
			#POST请求预处理
				if not request.content_type:
				#无正文类型信息返回时
					return web.HTTPBadRequest('Missing Content-Type.')
				ct = request.content_type.lower()
				if ct.startswith('application/json'):
				#处理json类型数据并传入字典中
					params = await request.json()
					if not isinstance(params,dict):
						return web.HTTPBadRequest('JSON body must be object.')
					kw = params
				elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
				#处理表单类型数据并传入字典中
					params = await request.post()
					kw = dict(**params)
				else:
				#暂不支持其他类型的数据
					return web.HTTPBadRequest('Unsupported Content-Type: %s' % request.content_type)
					
			if request.method == 'GET':
			#GET请求预处理
				qs = request.query_string	#获取url中的请求参数集，如name=gavin
				if qs:
					#将参数传入字典中
					kw = dict()
					for k, v in parse.parse_qs(qs,True).items():
						kw[k] = v[0]
		#请求无请求参数时
		if kw is None:
			kw = dict(**request.match_info)
			# Read-only property with AbstractMatchInfo instance for result of route resolving
		else:
		#参数字典收集请求参数
			if not self._has_var_kw_arg and self._named_kw_args:
				copy = dict()
				for name in self._named_kw_args:
					if name in kw:
						copy[name] = kw[name]
				kw =copy
				for k,v in request.match_info.items():
					if k in kw:
						logging.warning('Duplicate arg name in named arg and kw args: %s' % k)
				kw[k] = v
		#有请求参数
		if self._has_reqest_arg:
			kw['request'] = request
		if self._required_kw_args:		
		#收集无默认值的关键字参数
			for name in self._required_kw_args:
				if not name in kw:	# 当存在关键字参数未被赋值时返回，例如 一般的账号注册时，没填入密码就提交注册申请时，提示密码未输入
					return web.HTTPBadRequest('Missing arguments: %s' % name)
		logging.info('call with args:%s' % str(kw))
		#调用处理函数，并传入请求参数进行请求处理
		try:
			r = await self._func(**kw)
			return r
		except APIError as e:
			return dict(error=e.error,data=e.date,message=e.message)
			

#④绑定属性


#添加静态资源路径
def add_static(app):
	#os.path.dirname(os.path.abspath(__file__)),获取脚本所在目录的绝对路径
	path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'static')	 #获得包含'static'的绝对路径
	app.router.add_static('/static/',path)	#添加静态资源路径
	logging.info('add static %s--%s' % ('/static/',path))

#将处理函数注册到web服务器程序的路由中
def add_route(app,fn):
	method = getattr(fn,'__method__',None)	#获取fn的method属性，无责为none
	path = getattr(fn,'__route__',None)		#获取fn的route属性，无责为none	
	if path is None or method is None:
		raise ValueError('@get or @post not define in %s' % str(fn))
	if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
	#当处理函数不是协程时，将其封装成协程
		fn = asyncio.coroutine(fn)
	logging.info('add route %s %s--%s(%s)' % (method,path,fn.__name__,', '.join(inspect.signature(fn).parameters.keys())))
	app.router.add_route(method,path,RequestHandler(app,fn))

#自动把handler模块里符合条件的函数注册
def add_routes(app,module_name):
	#从上方符合条件的模块里，查找模块
	n = module_name.rfind('.')
	#没有匹配项时
	if n == (-1):
		#提交一个模块获取模块名字
		mod = __import__(module_name,globals(),locals())
	else:
		#添加模块属性name,并赋值给mod
		name = module_name[n+1:]
		mod = getattr(__import__(module_name[:n],globals(),locals(),[name]),name)
	for attr in dir(mod):	#dir(mod)获取模块的所有属性
		if attr.startswith('_'):
			continue	#略过所有私有属性
		fn = getattr(mod,attr)	#获取属性的值,可以是一个method
		if callable(fn):	#判断fn函数是否可调用
			method = getattr(fn,'__method__',None)
			path = getattr(fn,'__route__',None)
			if method and path:
				add_route(app,fn)
		
		
		
		
		
	

	
	
	
				
					
			
		
