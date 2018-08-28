# -*- coding: utf-8 -*-
import asyncio,os,inspect,logging,functools
from aiohttp import web
from urllib import parse
from apis import APIError


#���ȱ�дurl�����������url��������


#@getװ��������������url,��http method-GET����
def get(path):
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args,**kw):
			return func(*args,**kw)
		wrapper.__method__ = 'GET'
		wrapper.__route__ = path
		return wrapper
	return decorator

#@postװ��������������url,��http method-POST����
def post(path):
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args,**kw):
			return func(*args,**kw)
		wrapper.__method__ = 'POST'
		wrapper.__route__ = path
		return wrapper
	return decorator


#������Ĳ�������


#��麯���Ƿ���request�����������ز���ֵ�������ڼ��ò����Ƿ��Ǻ��������һ�������������׳��쳣
def has_reqest_arg(fn):
	params = inspect.signatre(fn).parameters	#��ȡ��������������Ϣ
	found =	False
	for name,param in params.items():
		if name == 'request':
			found = True
			continue	#�˳��ô�ѭ��
		#�����request�������һ�����λ�ò������׳��쳣
		if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
			raise ValueError('request parameter must be the last named parameter in function: %s%s' % (fn.__name__,str(sig)))
	return found
	
#��麯���Ƿ��йؼ��ֲ����������ز���ֵ
def has_var_kw_arg(fn):
	params = inspect.signatre(fn).parameters	#��ȡ��������������Ϣ
	for name,param in params.items():
		if param.kind == inspect.Parameter.VAR_KEYWORD:
			return True
			
#��麯���Ƿ��������ؼ��ֲ��������ز���ֵ
def has_named_kw_arg(fn):
	params = inspect.signatre(fn).parameters	#��ȡ��������������Ϣ
	for name,param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY:
			return True
	
#���������������ؼ��ֲ�����ΪԪ�淵��
def get_named_kw_args(fn):
	args = []
	params = inspect.signatre(fn).parameters	#��ȡ��������������Ϣ]
	for name,param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY:
			args.append(name)
	return tuple(args)

#������������Ĭ��ֵ�Ĺؼ��ֲ�����ΪԪ�淵��
def get_required_kw_args(fn):
	args = []
	params = inspect.signatre(fn).parameters	#��ȡ��������������Ϣ]
	for name,param in params.items():
		if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
			# param.kind : describes how argument values are bound to the parameter.
			# KEYWORD_ONLY : value must be supplied as keyword argument, which appear after a * or *args
			# param.default : the default value for the parameter,if has no default value,this is set to Parameter.empty
			# Parameter.empty : a special class-level marker to specify absence of default values and annotations
			args.append(name)
	return tuple(args)
	

#�۶��Ϸ��Ĵ��������з�װ����������
class RequestHandler(object):
	def __init__(self,app,fn):
		# app : an application instance for registering the fn
		# fn : a request handler with a particular HTTP method and path
		self._app = app
		self._func = fn
		self._has_reqest_arg = has_reqest_arg(fn)	#��麯���Ƿ���request�����������ز���ֵ�������ڼ��ò����Ƿ��Ǻ��������һ�������������׳��쳣
		self._has_var_kw_arg = has_var_kw_arg(fn)	#��麯���Ƿ��йؼ��ֲ����������ز���ֵ
		self._has_named_kw_arg = has_named_kw_arg(fn)	#��麯���Ƿ��������ؼ��ֲ��������ز���ֵ
		self._named_kw_args = get_named_kw_args(fn)		#���������������ؼ��ֲ�����ΪԪ�淵��
		self._required_kw_args = get_required_kw_args(fn)	#������������Ĭ��ֵ�Ĺؼ��ֲ�����ΪԪ�淵��
	
	#��������򣬱�����һ��Э�̣�������һ������ʵ����Ϊ��Ψһ�Ĳ�����������һ��streamresponse����ʵ��	
	async def __call__(self,request):
		kw = None
		# ������Ĵ��������� �ؼ��ֲ����� �� �����ؼ��ֲ��� �� request����
		if self._has_var_kw_arg or self._has_named_kw_arg or self._required_kw_args:
			if request.method == 'POST':
			#POST����Ԥ����
				if not request.content_type:
				#������������Ϣ����ʱ
					return web.HTTPBadRequest('Missing Content-Type.')
				ct = request.content_type.lower()
				if ct.startswith('application/json'):
				#����json�������ݲ������ֵ���
					params = await request.json()
					if not isinstance(params,dict):
						return web.HTTPBadRequest('JSON body must be object.')
					kw = params
				elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
				#������������ݲ������ֵ���
					params = await request.post()
					kw = dict(**params)
				else:
				#�ݲ�֧���������͵�����
					return web.HTTPBadRequest('Unsupported Content-Type: %s' % request.content_type)
					
			if request.method == 'GET':
			#GET����Ԥ����
				qs = request.query_string	#��ȡurl�е��������������name=gavin
				if qs:
					#�����������ֵ���
					kw = dict()
					for k, v in parse.parse_qs(qs,True).items():
						kw[k] = v[0]
		#�������������ʱ
		if kw is None:
			kw = dict(**request.match_info)
			# Read-only property with AbstractMatchInfo instance for result of route resolving
		else:
		#�����ֵ��ռ��������
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
		#���������
		if self._has_reqest_arg:
			kw['request'] = request
		if self._required_kw_args:		
		#�ռ���Ĭ��ֵ�Ĺؼ��ֲ���
			for name in self._required_kw_args:
				if not name in kw:	# �����ڹؼ��ֲ���δ����ֵʱ���أ����� һ����˺�ע��ʱ��û����������ύע������ʱ����ʾ����δ����
					return web.HTTPBadRequest('Missing arguments: %s' % name)
		logging.info('call with args:%s' % str(kw))
		#���ô������������������������������
		try:
			r = await self._func(**kw)
			return r
		except APIError as e:
			return dict(error=e.error,data=e.date,message=e.message)
			

#�ܰ�����


#��Ӿ�̬��Դ·��
def add_static(app):
	#os.path.dirname(os.path.abspath(__file__)),��ȡ�ű�����Ŀ¼�ľ���·��
	path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'static')	 #��ð���'static'�ľ���·��
	app.router.add_static('/static/',path)	#��Ӿ�̬��Դ·��
	logging.info('add static %s--%s' % ('/static/',path))

#��������ע�ᵽweb�����������·����
def add_route(app,fn):
	method = getattr(fn,'__method__',None)	#��ȡfn��method���ԣ�����Ϊnone
	path = getattr(fn,'__route__',None)		#��ȡfn��route���ԣ�����Ϊnone	
	if path is None or method is None:
		raise ValueError('@get or @post not define in %s' % str(fn))
	if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
	#������������Э��ʱ�������װ��Э��
		fn = asyncio.coroutine(fn)
	logging.info('add route %s %s--%s(%s)' % (method,path,fn.__name__,', '.join(inspect.signature(fn).parameters.keys())))
	app.router.add_route(method,path,RequestHandler(app,fn))

#�Զ���handlerģ������������ĺ���ע��
def add_routes(app,module_name):
	#���Ϸ�����������ģ�������ģ��
	n = module_name.rfind('.')
	#û��ƥ����ʱ
	if n == (-1):
		#�ύһ��ģ���ȡģ������
		mod = __import__(module_name,globals(),locals())
	else:
		#���ģ������name,����ֵ��mod
		name = module_name[n+1:]
		mod = getattr(__import__(module_name[:n],globals(),locals(),[name]),name)
	for attr in dir(mod):	#dir(mod)��ȡģ�����������
		if attr.startswith('_'):
			continue	#�Թ�����˽������
		fn = getattr(mod,attr)	#��ȡ���Ե�ֵ,������һ��method
		if callable(fn):	#�ж�fn�����Ƿ�ɵ���
			method = getattr(fn,'__method__',None)
			path = getattr(fn,'__route__',None)
			if method and path:
				add_route(app,fn)
		
		
		
		
		
	

	
	
	
				
					
			
		
