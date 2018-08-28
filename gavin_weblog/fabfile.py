#-*- coding: utf-8 -*-
#自动化部署脚本；将本地程序打包上传到服务器，并删除原有包，解压，重置www的软链接，程序相关服务和进程
from fabric.api import *


#服务器配置
env.user = 'root'
env.sudo_user = 'root'
env.password = '2018tiaocao'
env.hosts = ['192.161.176.84','155.94.191.156']

#数据库配置
db_user = 'www-data'
db_password ='www-data'

#压缩对象
_TAR_FILE = 'my_blog.tar.gz'

#压缩包上传的目录
_REMOTE_TMP_TAR = '/tmp/%s' % _TAR_FILE

#解压文件所在目录
_REMOTE_BASE_DIR = 'srv/gavin_weblog'


#返回当前路径
def _current_path():
	return os.path.abspath('.')

#返回当前时间
def _now():
	return datetime.now().strftime('%y-%m-%d_%H.%M.%S')

#在服务器上转储整个数据库，并备份到本地
def backup():
	dt = _now()
	f = 'backup-gavin_weblog-%s.sql' % dt		#通过当前时间构造文件名
	#数据库转储至tmp
	with cd('/tmp'):
		run('mysqldump --user=%s --password=%s --skip-opt --add-drop-table --default-character-set=utf8 --quick awesome > %s' % (db_user, db_password, f))		#mysqldump将数据导出，将数据备份到f
		run('tar -czvf %s.tar.gz %s' % (f,f))		#将f压缩生成新的压缩文件
		get('%s.tar.gz' % f,'%s/backup/' % _current_path())		#将压缩文件备份到新的目录
		run('rm -f %s' % f)		#删除f文件
		run('rm -f %s.tar.gz' % f)		#删除压缩文件

#打包；将所有文件打包		
def build():
	includes = ['static','templates','*.py','tubiao.ico','transwarp',]
	excludes = ['test','.*','*.pyc','*.pyo']
	local('rm -f dist/%s' % _TAR_FILE)		#先删除压缩文件
	with lcd(os.path.join(_current_path(),'www')):		#with lcd(path)可以把当前命令的目录设定为lcd()指定的目录，即_current_path(www)
		cmd = ['tar','--dereference','-czvf','../dist/%s' % _TAR_FILE]		#构建列表
		cmd.extend(['--exclude = \'%s\'' % ex for ex in excludes])		#extend() 函数在列表末尾追加另一个列表（用新列表扩展老的列表返回老列表）。
		cmd.extend(includes)
		local(' '.join(cmd))		#将cmd,includes,excludes组合成一个列表
		
def deploy():
	newdir = 'www-%s' % _now()
	run('rm -f %s' % _REMOTE_TMP_TAR)		#先删除服务器上老压缩包文件
	put('dist/%s' % _TAR_FILE,_REMOTE_TMP_TAR)		#将本机压缩包文件上传到服务器
	#创建新文件夹放置解压文件
	with cd(_REMOTE_BASE_DIR):
		sudo('mkdir %s' % newdir)
	#将服务器上压缩文件，减压到新目录
	with cd('%s/%s' % (_REMOTE_BASE_DIR,newdir)):
		sudo('tar -xzvf %s' % _REMOTE_TMP_TAR)
	#删除原来的程序文件，将软链接映射到新的解压文件夹
	with cd(_REMOTE_BASE_DIR):
		sudo('rm -f www')		#删除老程序
		sudo('ln -s %s www' % newdir)		#将软链接从www映射到新文件夹
		#重置软链接
		sudo('chown www-date:www-date www')
		sudo('chown -R www-date:www-date %s' % newdir)
	#重置应用程序；并重启nginx服务
	with settings(warn_only = True):
		sudo('supervisorctl stop gavin_weblog')
		sudo('supervisorctl start gavin_weblog')
		sudo('/etc/init.d/nginx reload')
		

RE_FILES = re.compile('\r?\n')

#回滚到前一版本
def rollback():
	with cd(_REMOTE_BASE_DIR):
		r = run('ls -p -1')		#各文件后面添加/，比如www/；-1
		#获取最新程序目录
		files = [s[:-1] for s in RE_FILES.split(r) if s.startswith('www-') and s.endswith('/')]		#startswith/endswith:判断是否以某字符开始/结束，www-是新目录名
		files.sort(cmp = lambda s1,s2: 1 if s1<s2 else -1)		#s1<s2正序，否则倒序
		#找软链接
		r = run('ls -l www') 		
		ss = r.split(' -> ')		#split分隔字符串分隔符，如m y s q l.split(  )=[m,y,s,q,l]
		if len(ss) != 2:
			print('ERROR: \'www\' is not a symbol link.')
			return
		current = ss[1]		#链接指向
		print('Found current symbol link points to: %s\n' % current)
		try:
			index = files.index(current)		#index()函数用于从列表中找出某个值第一个匹配项的索引位置。
		except ValueError as e:
			print('ERROR: symbol link is invalid.')
			return
		if len(files) == index+1:		#最后一个
			print('ERROR: already the oldest version.')
		old = files[index+1]
		print('=================')
		#验证
		for f in files:
			if f == current:
				print('      Current ---> %s' % current)
			elif f == old:
				print('  Rollback to ---> %s' % old)
			else:
				print('                   %s' % f)
		print('=================')		
		print('')	
		yn = raw_input('continue? y/N ')
		if yn != 'y' and yn != 'Y':
			print('rollback cancelled')
			return
		print('start rollback..')
		sudo('rm -f www')
		sudo('ln -s %s www' % old)
		sudo('chown www-data:www-data www')
		with settings(warn_only = True):
			sudo('supervisorctl stop gavin_weblog')
			sudo('supervisorctl start gavin_weblog')
			sudo('/etc/init.d/nginx reload')
		print('rollbacked ok')

#恢复数据库到本地		
def restore2local():
    '''
    Restore db to local
    '''
    backup_dir = os.path.join(_current_path(), 'backup')
    fs = os.listdir(backup_dir)
    files = [f for f in fs if f.startswith('backup-') and f.endswith('.sql.tar.gz')]
    files.sort(cmp=lambda s1, s2: 1 if s1 < s2 else -1)
    if len(files)==0:
        print ('No backup files found.')
        return
    print ('Found %s backup files:' % len(files))
    print ('==================================================')
    n = 0
    for f in files:
        print ('%s: %s' % (n, f))
        n = n + 1
    print ('==================================================')
    print ('')
    try:
        num = int(raw_input ('Restore file: '))
    except ValueError:
        print ('Invalid file number.')
        return
    restore_file = files[num]
    yn = raw_input('Restore file %s: %s? y/N ' % (num, restore_file))
    if yn != 'y' and yn != 'Y':
        print ('Restore cancelled.')
        return
    print ('Start restore to local database...')
    p = raw_input('Input mysql root password: ')
    sqls = [
        'drop database if exists awesome;',
        'create database awesome;',
        'grant select, insert, update, delete on awesome.* to \'%s\'@\'localhost\' identified by \'%s\';' % (db_user, db_password)
    ]
    for sql in sqls:
        local(r'mysql -uroot -p%s -e "%s"' % (p, sql))
    with lcd(backup_dir):
        local('tar zxvf %s' % restore_file)
    local(r'mysql -uroot -p%s awesome < backup/%s' % (p, restore_file[:-7]))		#用awesome?
    with lcd(backup_dir):
        local('rm -f %s' % restore_file[:-7])
		

	
	
	
		
		
		
	
