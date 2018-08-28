#-*- coding: utf-8 -*-
#监测器，利用watchdog监测目录中文件的变化，变化后通过subprocess来控制进程kill,start,restart
import os,sys,time,subprocess
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


#打印日志
def log(s):
	print('[Monitor] %s' % s)

#定义类实现目录文件变化时，重启进程
class MyFileSystemEventHandler(FileSystemEventHandler):
	def __init__(self,fn):
		super(MyFileSystemEventHandler,self).__init__()
		self.restart = fn
		
	def one_any_event(self,event):
		if event.src_path.endswith('.py'):		#监测以.py结尾的文件，观察是否变化
			log('Python source file changed: %s' % event.src_path)
			self.restart()


#默认参数
command = ['echo','ok']
process = None

#关闭进程
def	kill_process():
	global process
	if process:
		log('kill process [%s]...' % process.pid)
		process.kill()
		process.wait()
		log('process ended with code %s' % process.returncode)
		process = None
		
#使用subprocess启动进程
def start_process():
	global process,command
	log('start process %s...' % ' '.join(command))
	process = subprocess.Popen(command,stdin = sys.stdin,stdout = sys.stdout,stderr = sys.stderr)		#使用标准输入，输出和标准错误作为参数启动进程

#重启进程
def restart_process():
	kill_process()
	start_process()
	
#启动监控程序
def start_watch(path,callback):
	observer = Observer()		#创建监控对象
	observer.schedule(MyFileSystemEventHandler(restart_process),path,recursive = True)		#使用.schedule来进行任务调度，即定时任务
	observer.start()		#启动任务
	log('watching directory %s...' % path)
	start_process()		#启动程序
	try:
		while True:
			time.sleep(0.5)
	except KeyboardInterrupt:
		observer.stop()
	observer.join()		#将进程加入监测任务
	
	if __name__ == 'main':
		argv = sys.argv[1:]
		if not argv:
			print('Usage: ./pymonitor your-script.py')
			exit(0)
		if argv[0] != 'python3':
			argv.insert(0,'python3')
		command = argv
		path = os.path.abspath('.')
		start_watch(path,None)
			
			
		
			
