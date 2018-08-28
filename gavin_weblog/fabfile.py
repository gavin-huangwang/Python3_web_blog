#-*- coding: utf-8 -*-
#�Զ�������ű��������س������ϴ�������������ɾ��ԭ�а�����ѹ������www�������ӣ�������ط���ͽ���
from fabric.api import *


#����������
env.user = 'root'
env.sudo_user = 'root'
env.password = '2018tiaocao'
env.hosts = ['192.161.176.84','155.94.191.156']

#���ݿ�����
db_user = 'www-data'
db_password ='www-data'

#ѹ������
_TAR_FILE = 'my_blog.tar.gz'

#ѹ�����ϴ���Ŀ¼
_REMOTE_TMP_TAR = '/tmp/%s' % _TAR_FILE

#��ѹ�ļ�����Ŀ¼
_REMOTE_BASE_DIR = 'srv/gavin_weblog'


#���ص�ǰ·��
def _current_path():
	return os.path.abspath('.')

#���ص�ǰʱ��
def _now():
	return datetime.now().strftime('%y-%m-%d_%H.%M.%S')

#�ڷ�������ת���������ݿ⣬�����ݵ�����
def backup():
	dt = _now()
	f = 'backup-gavin_weblog-%s.sql' % dt		#ͨ����ǰʱ�乹���ļ���
	#���ݿ�ת����tmp
	with cd('/tmp'):
		run('mysqldump --user=%s --password=%s --skip-opt --add-drop-table --default-character-set=utf8 --quick awesome > %s' % (db_user, db_password, f))		#mysqldump�����ݵ����������ݱ��ݵ�f
		run('tar -czvf %s.tar.gz %s' % (f,f))		#��fѹ�������µ�ѹ���ļ�
		get('%s.tar.gz' % f,'%s/backup/' % _current_path())		#��ѹ���ļ����ݵ��µ�Ŀ¼
		run('rm -f %s' % f)		#ɾ��f�ļ�
		run('rm -f %s.tar.gz' % f)		#ɾ��ѹ���ļ�

#������������ļ����		
def build():
	includes = ['static','templates','*.py','tubiao.ico','transwarp',]
	excludes = ['test','.*','*.pyc','*.pyo']
	local('rm -f dist/%s' % _TAR_FILE)		#��ɾ��ѹ���ļ�
	with lcd(os.path.join(_current_path(),'www')):		#with lcd(path)���԰ѵ�ǰ�����Ŀ¼�趨Ϊlcd()ָ����Ŀ¼����_current_path(www)
		cmd = ['tar','--dereference','-czvf','../dist/%s' % _TAR_FILE]		#�����б�
		cmd.extend(['--exclude = \'%s\'' % ex for ex in excludes])		#extend() �������б�ĩβ׷����һ���б������б���չ�ϵ��б������б���
		cmd.extend(includes)
		local(' '.join(cmd))		#��cmd,includes,excludes��ϳ�һ���б�
		
def deploy():
	newdir = 'www-%s' % _now()
	run('rm -f %s' % _REMOTE_TMP_TAR)		#��ɾ������������ѹ�����ļ�
	put('dist/%s' % _TAR_FILE,_REMOTE_TMP_TAR)		#������ѹ�����ļ��ϴ���������
	#�������ļ��з��ý�ѹ�ļ�
	with cd(_REMOTE_BASE_DIR):
		sudo('mkdir %s' % newdir)
	#����������ѹ���ļ�����ѹ����Ŀ¼
	with cd('%s/%s' % (_REMOTE_BASE_DIR,newdir)):
		sudo('tar -xzvf %s' % _REMOTE_TMP_TAR)
	#ɾ��ԭ���ĳ����ļ�����������ӳ�䵽�µĽ�ѹ�ļ���
	with cd(_REMOTE_BASE_DIR):
		sudo('rm -f www')		#ɾ���ϳ���
		sudo('ln -s %s www' % newdir)		#�������Ӵ�wwwӳ�䵽���ļ���
		#����������
		sudo('chown www-date:www-date www')
		sudo('chown -R www-date:www-date %s' % newdir)
	#����Ӧ�ó��򣻲�����nginx����
	with settings(warn_only = True):
		sudo('supervisorctl stop gavin_weblog')
		sudo('supervisorctl start gavin_weblog')
		sudo('/etc/init.d/nginx reload')
		

RE_FILES = re.compile('\r?\n')

#�ع���ǰһ�汾
def rollback():
	with cd(_REMOTE_BASE_DIR):
		r = run('ls -p -1')		#���ļ��������/������www/��-1
		#��ȡ���³���Ŀ¼
		files = [s[:-1] for s in RE_FILES.split(r) if s.startswith('www-') and s.endswith('/')]		#startswith/endswith:�ж��Ƿ���ĳ�ַ���ʼ/������www-����Ŀ¼��
		files.sort(cmp = lambda s1,s2: 1 if s1<s2 else -1)		#s1<s2���򣬷�����
		#��������
		r = run('ls -l www') 		
		ss = r.split(' -> ')		#split�ָ��ַ����ָ�������m y s q l.split(  )=[m,y,s,q,l]
		if len(ss) != 2:
			print('ERROR: \'www\' is not a symbol link.')
			return
		current = ss[1]		#����ָ��
		print('Found current symbol link points to: %s\n' % current)
		try:
			index = files.index(current)		#index()�������ڴ��б����ҳ�ĳ��ֵ��һ��ƥ���������λ�á�
		except ValueError as e:
			print('ERROR: symbol link is invalid.')
			return
		if len(files) == index+1:		#���һ��
			print('ERROR: already the oldest version.')
		old = files[index+1]
		print('=================')
		#��֤
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

#�ָ����ݿ⵽����		
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
    local(r'mysql -uroot -p%s awesome < backup/%s' % (p, restore_file[:-7]))		#��awesome?
    with lcd(backup_dir):
        local('rm -f %s' % restore_file[:-7])
		

	
	
	
		
		
		
	
