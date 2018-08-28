# -*- coding:utf-8 -*- 
from aiohttp import web
import asyncio,os,json,time,hashlib
#��logging��basicConfig�������������ں����ж����ˣ��൱����д������
import logging; logging.basicConfig(level=logging.INFO)
from jinja2 import Environment,FileSystemLoader
from datetime import datetime
import orm
import config
from web_frame import add_routes,add_static
from models import User
from handlers import cookie2user,COOKIE_NAME


#ģ�������ʼ��
def init_jinja2(app,**kw):
	logging.info('init jinja2')
	options = dict(
		autoescape = kw.get('autoescape',True),		#Ĭ�ϴ��Զ�ת��ת���ַ�
		block_start_string = kw.get('block_start_string','{%'),		#ģ����ƿ�/�����������ַ���
		block_end_string = kw.get('block_end_string','%}'),		#ģ����ƿ�������ַ���
		variable_start_string = kw.get('variable_start_string','{{'),		#ģ���б����������ַ���
		variable_end_string = kw.get('variable_end_string','}}'),		#ģ���б����������ַ���
		auto_reload = kw.get('auto_reload',True),
	)
	path = kw.get('path',None)
	if path is None:
		path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'templates')		#��ȡģ��·��
	logging.info('set jinja2 templates path: %s' % path)
	env = Environment(loader=FileSystemLoader(path),**options)		#���ļ�ϵͳ����ģ��
	filters = kw.get('filters',None)		#���Ի�ȡ������
	if filters is not None:
		for name,f in filters.items():
			env.filters[name] = f
	#��webʵ�������ģ������
	app['__templating__'] = env

#�м�����൱��a��b֮���ǽ�������ڴ�������ǰ�������������֤��ɸѡ����¼�Ȳ���	
async def logger_factory(app,handler):
	async def logger(request):
		logging.info('Request: %s %s' % (request.method,request.path))		#��ӡ���������ͺ͵�ַ
		return (await handler(request))		#������������
	return logger
	
#post�����м��	
async def data_factory(app,handler):
	async def parse_data(request):
		if request.method == 'POST':
			if request.content_type.startswith('application/json'):
				request.__data__ = await request.json()
				logging.info('request json: %s' % str(request.__data__))
			elif request.content_type.startswith('application/x-www-form-urlencoded'):
				request.__data__ = await request.post()
				logging.info('request form: %s' % str(request.__data__))
		return (await handler(request))		#������������
	return parse_data
#��Ӧ���м��
async def response_factory(app,handler):
	#�Դ���������Ӧ���д���
	async def response(request):
		logging.info('reponse handler')
		r = await handler(request)
		#������Ӧ��
		if isinstance(r,web.StreamResponse):
			return r
		#�����ֽ�����Ӧ
		if isinstance(r,bytes):
			resp = web.Response(body = r)
			resp.content_type = 'application/octet-stream'
			return resp
		#�����ַ�������Ӧ
		if isinstance(r,str):
			#�����ض�����Ӧ
			if r.startswith('redirect:'):	
				return web.HTTPFound(r[9:])
			resp = web.Response(body = r.encode('utf-8'))
			resp.content_type = 'text/html;charset=utf-8'
			return resp		#����Html
		#�����ֵ�����Ӧ
		if isinstance(r,dict):
			template = r.get('__template__')
			if template is None:
				#����json����Ӧ
				resp = web.Response(body = json.dumps(r,ensure_ascii = False,default=lambda o: o.__dict__).encode('utf-8'))
				resp.content_type = 'application/json;charset=utf-8'
				return resp
			else:
				#��ȡģ�岢������Ӧ����������Ⱦ
				r['__user__'] = request.__user__
				resp = web.Response(body = app['__templating__'].get_template(template).render(**r).encode('utf-8'))
				resp.content_type = 'text/html;charset=utf-8'
				return resp
		#������Ӧ��
		if isinstance(r,int) and t >= 100 and t <= 600:
			return web.Response(t)
		#������������Ϣ��Ӧ��
		if isinstance(r,tuple) and len(r) == 2:
			t,m = r
			if isinstance(t,int) and t >= 100 and t <= 600:
				return web.Response(t,str(m))
		
		#������Ӧ����
		resp = web.Response(body = str(r).encode('utf-8'))
		resp.content_type = 'text/plain;charset=utf-8'
		return resp
	return response
	
#����cookie��������cookie�л�ȡ���˺���Ϣ�󶨵�������
async def auth_factory(app,handler):
	async def auth(request):
		logging.info('check user:%s %s' % (request.method,request.path))
		request.__user__ = None
		cookie_str = request.cookies.get(COOKIE_NAME)
		if cookie_str:
			user = await cookie2user(cookie_str)
			if user:
				logging.info('set current user: %s' % user.email)
				request.__user__ = user		#����cookie�л�ȡ���˺���Ϣ�󶨵�����
			if request.path.startswith('/manage/') and (request.__user__ is None or not request.__user__.admin):		#���������ǹ���ҳ��/�û�δ��½/���admin�û�ʱ,��ת����½ҳ
				return web.HTTPFound('/signin')
		return (await handler(request))
	return auth
	
#����ʱ�䴦����
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
	dt = datetime.fromtimestamp(t)	#��timestampת��Ϊdatetime
	return u'%s-%s-%s' % (dt.year,dt.month,dt.day)
	
	
#װ���������ǽ�init������Ϊ��������coroutine����������Э�̣�
#' ���������г��򣺴���webʵ�����򣬸�ʵ�������·�ɺʹ����������з������������˿������͵�·�ɴ��� '
async def init(loop):
	await orm.create_pool(loop = loop,**config.configs.db)
	#����Ӧ�ö���
	app = web.Application(loop = loop,middlewares = [logger_factory,data_factory,response_factory,auth_factory])		#ִ���м��
	#ģ���ʼ��
	init_jinja2(app,filters = dict(datetime = datetime_filter))
	#��ͼ����ģ��MVC����ַ��ҳ�����
	add_routes(app,'handlers')
	add_static(app)
	#ѭ�������������µ�����ʱ�������µķ���
	srv = await loop.create_server(app.make_handler(),'127.0.0.1',9000)
	#loggingģ��Ĳ����������ӡ��־��Ϣ
	logging.info('server started at http://127.0.0.1:9000...')
	return srv

#������ȡ����
loop = asyncio.get_event_loop()
#��ȡ���������������񣬼�ִ�������ķ���
loop.run_until_complete(init(loop))
#�����񣬿��Ƿ������������
loop.run_forever()	
