# -*- coding:utf-8 -*- 
from aiohttp import web
import asyncio,os,json,time,hashlib
#对logging的basicConfig传参数，参数在函数中定义了，相当于重写函数；
import logging; logging.basicConfig(level=logging.INFO)
from jinja2 import Environment,FileSystemLoader
from datetime import datetime
import orm
import config
from web_frame import add_routes,add_static
from models import User
from handlers import cookie2user,COOKIE_NAME


#模板引擎初始化
def init_jinja2(app,**kw):
	logging.info('init jinja2')
	options = dict(
		autoescape = kw.get('autoescape',True),		#默认打开自动转义转义字符
		block_start_string = kw.get('block_start_string','{%'),		#模板控制快/方法启动的字符串
		block_end_string = kw.get('block_end_string','%}'),		#模板控制快结束的字符串
		variable_start_string = kw.get('variable_start_string','{{'),		#模板中变量启动的字符串
		variable_end_string = kw.get('variable_end_string','}}'),		#模板中变量结束的字符串
		auto_reload = kw.get('auto_reload',True),
	)
	path = kw.get('path',None)
	if path is None:
		path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'templates')		#获取模板路径
	logging.info('set jinja2 templates path: %s' % path)
	env = Environment(loader=FileSystemLoader(path),**options)		#用文件系统加载模板
	filters = kw.get('filters',None)		#尝试获取过滤器
	if filters is not None:
		for name,f in filters.items():
			env.filters[name] = f
	#给web实例程序绑定模板属性
	app['__templating__'] = env

#中间件，相当于a，b之间的墙，可以在处理请求前，对请求进行验证，筛选，记录等操作	
async def logger_factory(app,handler):
	async def logger(request):
		logging.info('Request: %s %s' % (request.method,request.path))		#打印出请求类型和地址
		return (await handler(request))		#继续处理请求
	return logger
	
#post请求中间件	
async def data_factory(app,handler):
	async def parse_data(request):
		if request.method == 'POST':
			if request.content_type.startswith('application/json'):
				request.__data__ = await request.json()
				logging.info('request json: %s' % str(request.__data__))
			elif request.content_type.startswith('application/x-www-form-urlencoded'):
				request.__data__ = await request.post()
				logging.info('request form: %s' % str(request.__data__))
		return (await handler(request))		#继续处理请求
	return parse_data
#响应的中间件
async def response_factory(app,handler):
	#对处理函数的响应进行处理
	async def response(request):
		logging.info('reponse handler')
		r = await handler(request)
		#处理响应流
		if isinstance(r,web.StreamResponse):
			return r
		#处理字节类响应
		if isinstance(r,bytes):
			resp = web.Response(body = r)
			resp.content_type = 'application/octet-stream'
			return resp
		#处理字符串类响应
		if isinstance(r,str):
			#返回重定向响应
			if r.startswith('redirect:'):	
				return web.HTTPFound(r[9:])
			resp = web.Response(body = r.encode('utf-8'))
			resp.content_type = 'text/html;charset=utf-8'
			return resp		#返回Html
		#处理字典类响应
		if isinstance(r,dict):
			template = r.get('__template__')
			if template is None:
				#返回json类响应
				resp = web.Response(body = json.dumps(r,ensure_ascii = False,default=lambda o: o.__dict__).encode('utf-8'))
				resp.content_type = 'application/json;charset=utf-8'
				return resp
			else:
				#获取模板并传入响应参数进行渲染
				r['__user__'] = request.__user__
				resp = web.Response(body = app['__templating__'].get_template(template).render(**r).encode('utf-8'))
				resp.content_type = 'text/html;charset=utf-8'
				return resp
		#处理响应码
		if isinstance(r,int) and t >= 100 and t <= 600:
			return web.Response(t)
		#处理有描述信息响应码
		if isinstance(r,tuple) and len(r) == 2:
			t,m = r
			if isinstance(t,int) and t >= 100 and t <= 600:
				return web.Response(t,str(m))
		
		#其他响应返回
		resp = web.Response(body = str(r).encode('utf-8'))
		resp.content_type = 'text/plain;charset=utf-8'
		return resp
	return response
	
#分析cookie，并将从cookie中获取的账号信息绑定到请求上
async def auth_factory(app,handler):
	async def auth(request):
		logging.info('check user:%s %s' % (request.method,request.path))
		request.__user__ = None
		cookie_str = request.cookies.get(COOKIE_NAME)
		if cookie_str:
			user = await cookie2user(cookie_str)
			if user:
				logging.info('set current user: %s' % user.email)
				request.__user__ = user		#将从cookie中获取到账号信息绑定到请求
			if request.path.startswith('/manage/') and (request.__user__ is None or not request.__user__.admin):		#如果请求的是管理页面/用户未登陆/或非admin用户时,跳转到登陆页
				return web.HTTPFound('/signin')
		return (await handler(request))
	return auth
	
#发布时间处理方法
def datetime_filter(t):
	delta = int(time.time() - t)
	if delta < 60:
		return u'1 minute ago'
	if delta < 3600:
		return u'%s minute ago' % (delta // 60)
	if delta < 86400:
		return u'%s hours ago' % (delta // 3600)
	if delta < 604800:
		return u'%s day ago' % (delta // 86400)
	dt = datetime.fromtimestamp(t)	#把timestamp转换为datetime
	return u'%s-%s-%s' % (dt.year,dt.month,dt.day)
	
	
#装饰器大意是将init函数作为参数调用coroutine方法来创建协程；
#' 服务器运行程序：创建web实例程序，该实例程序绑定路由和处理函数，运行服务器，监听端口请求，送到路由处理 '
async def init(loop):
	await orm.create_pool(loop = loop,**config.configs.db)
	#创建应用对象
	app = web.Application(loop = loop,middlewares = [logger_factory,data_factory,response_factory,auth_factory])		#执行中间件
	#模板初始化
	init_jinja2(app,filters = dict(datetime = datetime_filter))
	#视图控制模块MVC将地址和页面关联
	add_routes(app,'handlers')
	add_static(app)
	#循环创建服务，有新的任务时，创建新的服务
	srv = await loop.create_server(app.make_handler(),'127.0.0.1',9000)
	#logging模块的参数，程序打印日志信息
	logging.info('server started at http://127.0.0.1:9000...')
	return srv

#持续获取任务
loop = asyncio.get_event_loop()
#获取到满足条件的任务，即执行驱动的方法
loop.run_until_complete(init(loop))
#检测服务，看是否有新任务过来
loop.run_forever()	
