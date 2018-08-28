# -*- coding: utf-8 -*-

import config_default

#��dict������Զ��壬��ʵ�������ȡֵ������k['v']=k.v
class Dict(dict):
	def __init__(self,names = (),values = (),**kw):
		super(Dict,self).__init__(**kw)
		for k,v in zip(names,values):	#zip����������װ����[��tuple��,()]���ݽṹ����zip([123],[45]])==[(1,4),(2,5)]
			self[k] = v

	def __getattr__(self,key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(r"'Dict' object has no attribute '%s'" % key)
			
	def __setattr__(self,key,value):
		self[key] = value

#defaults,override���������ļ��ĸ����㷨	
def merge(defaults,override):
	#��ȡ���µ�����
	r = {}
	for k,v in defaults.items():
		if k in override:
			if isinstance(v,dict):
				r[k] = merge(v,override[k])
			else:
				r[k] = override[k]	#����ʹ��override������
		else:
			r[k] = v
	return r

#ת����dict��	
def toDict(d):
	D = Dict()
	for k,v in d.items():
		D[k] = toDict(v) if isinstance(v,dict) else v
	return D
	
configs = config_default.configs	#condig_default�ļ���configs

try:
	import config_override
	configs = merge(configs,config_override.configs)
except ImportError:
	pass

configs = toDict(configs)









				
		
