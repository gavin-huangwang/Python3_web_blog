# -*- coding: utf-8 -*-
#MVC/MVVM handlers
from web_frame import get,post
import re,time,json,logging,hashlib,base64,asyncio
from models import Blog, User, Comment, next_id
from apis import Page,APIValueError,APIResourceNotFoundError
from config import configs
import markdown2
from aiohttp import web


#cokkie默认值
COOKIE_NAME = 'jlsession'
_COOKIE_KEY = 'winner takes all'		#用来加盐

#用户验证/管理员
def check_admin(request):
	if request.__user__ is None or not request.__user__.admin:
		raise APIPermissionError

#获取页码	
def get_page_index(page_str):
	p = 1
	try:
		p = int(page_str)
	except ValueError as e:
		pass
	if p<1:
		p = 1
	return p

#把文本拼接成html格式文件	
def text2html(text):
	lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
	return ''.join(lines)

#cookie加密方法,以用户id,过期日期，密码来计算
def user2cookie(user,max_age):
	expires = str(int(time.time()+max_age))		#计算过期时间
	s = '%s-%s-%s-%s' % (user.id,user.passwd,expires,_COOKIE_KEY)		#通过这四个元素，构建对象用来加盐创建cookie
	L = [user.id,expires,hashlib.sha1(s.encode('utf-8')).hexdigest()]
	return '-'.join(L)
	
#cookie解密方法
async def cookie2user(cookie_str):
	if not cookie_str:
		return None
	try:
		L = cookie_str.split('-')
		if len(L) == 3:
			return None
		uid,expires,sha1 = L
		if int(expires)<time.time():	#cookie过期
			return None
		user = await User.find(uid)
		if user is None:		#新用户
			return None
		s = '%s-%s-%s-%s' % (user.id,user.passwd,expires,_COOKIE_KEY)
		if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():		#服务器返回的sha1cookie和客户端对输入账号计算出的sha值不一致	
			logging.info('invalid sha1')
			return None
		user.passwd = '$$$$$$'
		return user
	except Exception as e:
		logging.exception(e)
		return None


#用户浏览页面


#MVVM,首页
@get('/')
async def index(*,page = '1'):
	page_index = get_page_index(page)
	num = await Blog.findNumber('count(id)')
	page = Page(num)
	if num == 0:
		blogs = []
	else:
		blogs = await Blog.findAll(orderBy='create_at desc',limit = (page.offset,page.limit))
	return {
		'__template__':'blogs.html',
		'page':page,
		'blogs':blogs,
	}

#MVVM，用户注册页面	
@get('/register')		
def register():
	return{ '__template__': 'register.html'}

#MVVM，用户登陆页面
@get('/signin')		
def signin():
	return{ '__template__': 'signin.html'}	
	
#MVVM，用户退出页面
@get('/signout')
def signout(request):
	referer = request.handers.get('Referer')
	r = web.HTTPFound(referer or '/')		#退出到参考页or首页
	r.set_cookie(COOKIE_NAME,'-deleted-',max_age = 0,httponly = True)		#退出后cookie被清空
	logging.info('user signed out.')
	return r		#响应的页面
	
#MVVM，查看日志
@get('/blog/{id}')
def get_blog(id):
	blog = yield from Blog.find(id)
	comments = yield from Comment.findAll('blog_id=?',[id],orderBy = 'created_at desc')
	for c in comments:
		c.html_content = text2html(c.content)
	blog.html_content = markdown2.markdown(blog.content)	#调用脚本对数据库操作
	return {
		'__template__':'blog.html',
		'blog':blog,
		'comments':comments,
	}
	

#管理页面


#待补
@get('/manage/')
def manage():
	return 'redirect:/manage/comments'
#日志列表页/管理页
@get('manage/blogs')
def manage_blogs(*,page='1'):
	return{
		'__template__':'manage_blogs.html',
		'page_index':get_page_index(page),
	}

#日志创建页
@get('/manage/blogs/create')
def manage_create_blog():
	return{
		'__template__':'manage_blog_edit.html',
		'id':'',
		'action':'/api/blogs',
	}

#日志修改页
@get('/manage/blogs/edit')
def manage_edit_blog(*,id):
	return{
		'__template__':'manage_blog_edit.html',
		'id':id,
		'action':'/api/blogs/%s' % id,
	}

#用户管理页
@get('/manage/users')
def manage_users(*,page='1'):
	return{
		'__template__':'manage_users.html',
		'page_index':get_page_index(page),
	}
	
#用户评论管理页
@get('/manage/comments')
def manage_comments(*,page='1'):
	return{
		'__template__':'manage_comments.html',
		'page_index':get_page_index(page),
	}


#后端API


#用户个人页--API
@get('/api/users')
async def api_get_users():
	users = await User.findAll(orderBy = 'created_at desc')
	for u in users:
		u.passwd = '******'
	return dict(users = users)

_reEmail = re.compile(r'^[0-9a-z\.\-\_]+\@[0-9a-z\-\_]+(\.[0-9a-z\-\_]+){1,4}$')		#使用正则匹配输入邮箱格式
_reSha1  = re.compile(r'^[0-9a-f]{40}$')		#SHA1不安全，后续升级

#用户注册--API，通过哈希算法计算
@post('/api/user')
async def api_register_user(*,email,name,passwd):
	#注册输入参数定义
	if not email or not _reEmail.match(email):		#未输入email/email格式不对
		raise APIValueError('input email error')
	if not name or not name.strip():		#未输入name/name中存在空格（未对输入字符定义易出现编码错误）
		raise APIValueError('input name error')
	if not passwd or not _reSha1.match(passwd):		#为输入passwd/passwd类型不满足正则定义
		raise APIValueError('input passwd error')
	#验证email是否已存在
	users_email = await User.findAll('email=?',[email])		#查找users表中的email账号
	if len(users_email)>0:
		raise APIError('register failed',users_email,'email is already in use')
	users_name = await User.findAll('name=?',[name])		#查找users表中的email账号
	if len(users_name)>0:
		raise APIError('register failed',users_name,'name is already in use')	
	#SHA1哈希算法对密码进行处理生成sha口令存储到数据库
	uid = next_id()
	sha1_Passwd = '%s:%s' % (uid,passwd)		#加盐，将uid和密码作为参数计算哈希值
	user = User(id = uid,name = name.strip(),email=email,passwd = hashlib.sha1(sha1_Passwd.encode('utf-8')).hexdigest(),image = 'about:blank')		#通过sha1加密hashlib.sha1('str').hexdigest()是固定格式
	await user.save()		#User对象保存到数据库
	#设置会话cookie
	r = web.Response()
	r.set_cookie(COOKIE_NAME,user2cookie(user,86400),max_age = 86400,httponly = True)		#httponly指定js不能获取cookie
	user.passwd = '$$$$$$'		#赋值方式清理内存中passwd,明码
	r.content_type = 'application/json'
	r.body = json.dumps(user,ensure_ascii = False).encode('utf-8')		#转换成json格式
	return r
	
#用户登陆验证--API
@post('/api/authenticate')
async def authenticate(*,email,passwd):
	if not email:
		raise APIValueError('email','Please Input Email')
	if not passwd:
		raise APIValueError('passwd','Passwd Error')
	users = await User.findAll('email=?',[email])
	if len(users)  == 0:
		raise APIValueError('email','email not register. ')
	user = users[0]
	sha1 = hashlib.sha1()
	sha1.update(user.id.encode('utf-8'))
	sha1.update(b':')
	sha1.update(passwd.encode('utf-8'))
	if user.passwd != sha1.hexdigest():
		raise APIValueError('passwd','invalid passwd')
	#验证ok,设置cookie
	r = web.Response()
	r.set_cookie(COOKIE_NAME,user2cookie(user,86400),max_age = 86400,httponly = True)		#cookie24小时失效，cookie无法被js获取
	user.passwd = '$$$$$$'
	r.content_type = 'application/json'
	r.body = json.dumps(user,ensure_ascii = False).encode('utf-8')
	return r		#响应的页面				


#查看blogs页面--API
@get('/api/blogs')
async def api_blogs(*,page='1'):
	page_index = get_page_index(page)
	num = await Blog.findNumber('count(id)')
	p = Page(num,page_index)
	if num == 0:
		return dict(page = p,blogs = ())
	blogs = await Blog.findAll(orderBy = 'created_at desc',limit = (p.offset,p.limit))
	return dict(page = p,blogs = blogs)
	
#查看单条blogs--API	
@get('/api/blogs/{id}')
def api_get_blog(*,id):
	blog = yield from Blog.find(id)
	return blog

#创建博客--API
@post('/api/blogs')
async def api_create_blog(request,*,name,summary,content):
	check_admin(request)	#创建博客前先验证用户
	if not name or name.strip():
		raise APIValueError('name','name cannot be empty.')
	if not summary or summary.strip():
		raise APIValueError('summary','summary cannot be empty.')
	if not content or content.strip():
		raise APIValueError('content','content cannot be empty.')
	blog = Blog(
				user_id = request.__user__.id,
				user_name = request.__user__.name,
				user_image = request.__user__.image,
				name = name.strip(),
				summary = summary.strip(),
				content = content.strip(),
				)
	await blog.save()
	return blog
	
#修改博客--API
@post('/api/blogs/{blog_id}')
async def api_edit_blog(blog_id,request,*,name,summary,content):
	check_admin(request)		#创建博客前先验证用户
	blog = await Blog.find(blog_id)
	if not name or name.strip():
		raise APIValueError('name','name cannot be empty.')
	if not summary or summary.strip():
		raise APIValueError('summary','summary cannot be empty.')
	if not content or content.strip():
		raise APIValueError('content','content cannot be empty.')
	blog.name = name.strip()
	blog.summary = summary.strip() 
	blog.content = content.strip() 
	await blog.update()
	return blog
	
#删除blogs--API
@post ('/api/blogs/{blog_id}/delete')
async def api_delete_blog(request,*,blog_id):
	check_admin(request)
	blog = await Blog.find(blog_id)
	await blog.remove()
	return dict(id = blog_id)


#查看comments页面--API
@get('/api/comments')
async def api_comments(*,page='1'):
	page_index = get_page_index(page)
	num = await Comment.findNumber('count(id)')
	p = Page(num,page_index)
	if num == 0:
		return dict(page = p,comments = ())
	comments = await Comment.findAll(orderBy = 'created_at desc',limit = (p.offset,p.limit))
	return dict(page = p,comments = comments)

#创建comments--API
@post('/api/blogs/{blog_id}/comments')
async def api_create_comments(blog_id,request,*,content):
	user = request.__user__
	if user is None:
		raise APIPermissionError('please signin first.')
	if not content or content.strip():
		raise APIValueError('content','content cannot be empty.')
	blog = await Blog.find(blog_id)
	if blog is None:
		raise APIResourceNotFoundError('Blog')
	comment = Comment(
				blog_id = blog.id,
				user_id = user.id,
				user_name = user.name,
				user_image = user.image,
				content = content.strip(),
				)
	await comment.save()
	return comment
	
#删除comments--API
@post ('/api/comments/{comment_id}/delete')
async def api_delete_comments(request,comment_id):
	check_admin(request)
	comment = await Comment.find(comment_id)
	if comment is None:
		raise APIResourceNotFoundError('Comment') 
	await comment.remove()
	return dict(id = comment_id)
	
	
	
	
	
	
	
	
