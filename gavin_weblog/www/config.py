# -*- coding: utf-8 -*-

import config_default

#对dict类进行自定义，以实现特殊的取值方法如k['v']=k.v
class Dict(dict):
	def __init__(self,names = (),values = (),**kw):
		super(Dict,self).__init__(**kw)
		for k,v in zip(names,values):	#zip方法将参数装换成[（tuple）,()]数据结构，如zip([123],[45]])==[(1,4),(2,5)]
			self[k] = v

	def __getattr__(self,key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(r"'Dict' object has no attribute '%s'" % key)
			
	def __setattr__(self,key,value):
		self[key] = value

#defaults,override两个配置文件的覆盖算法	
def merge(defaults,override):
	#读取更新的配置
	r = {}
	for k,v in defaults.items():
		if k in override:
			if isinstance(v,dict):
				r[k] = merge(v,override[k])
			else:
				r[k] = override[k]	#优先使用override的配置
		else:
			r[k] = v
	return r

#转换成dict类	
def toDict(d):
	D = Dict()
	for k,v in d.items():
		D[k] = toDict(v) if isinstance(v,dict) else v
	return D
	
configs = config_default.configs	#condig_default文件的configs

try:
	import config_override
	configs = merge(configs,config_override.configs)
except ImportError:
	pass

configs = toDict(configs)









				
		
