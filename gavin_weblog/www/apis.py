# -*- coding: utf-8 -*-
#json api 定义
import json,logging,inspect,functools


#显示页面的类，根据输入内容条数，每页最大显示数和当前显示的页面来分析总共有多少页，上下翻页
class Page(object):
	def __init__(self,item_count,page_index=1,page_size=10):	#通过项目计数，页面索引，即页面最大尺寸来进行分页如Page(101,10,10)表示有101条内容，每页最多10条内容，此时展示的是第10页
		
        #Init Pagination by item_count, page_index and page_size.
		'''
        >>> p1 = Page(100, 1)
        >>> p1.page_count
        10
        >>> p1.offset
        0
        >>> p1.limit
        10
        >>> p2 = Page(90, 9, 10)
        >>> p2.page_count
        9
        >>> p2.offset
        80
        >>> p2.limit
        10
        >>> p3 = Page(91, 10, 10)
        >>> p3.page_count
        10
        >>> p3.offset
        90
        >>> p3.limit
        10
        '''
		self.item_count = item_count
		self.page_size = page_size
		self.page_count = item_count//page_size+(1 if item_count%page_size>0 else 0)
		if (item_count ==0) or (page_index>page_count):		#此时无内容，展示第一页
			self.offset = 0	
			self.limit = 0
			self.page_index = 1
		else:
			self.offset = self.page_size*(page_index-1)		#页面偏移量，表示显示页面从第几条内容开始显示的
			self.limit = self.page_size		#每页最大条数
			self.page_index = page_index
		self.has_next = self.page_index<self.page_count		#下一页，<在这是偏移符号，表示从当前页面向最大页面偏移，每次加1
		self.has_previous = self.page_index>1		#上一页，>向前偏移一位
		
	def __str__(self):		#类中定义用来给print调用的，会将内容转化为字符串输出即print(Page)
		return 'item_count: %s, page_count: %s, page_index: %s, page_size: %s, offset: %s, limit: %s' % (self.item_count, self.page_count, self.page_index, self.page_size, self.offset, self.limit)
	
	__repr__ = __str__		#命令行中显示的信息和print(Page)一样	
		
#基本的APIError，它包含错误（required）、数据（optional）和消息（optional）
class APIError(Exception):
	def __init__(self,error,data = '',message = ''):
		super(APIError,self).__init__(message)
		self.error = error
		self.data = data
		slef.message = message

#表示输入值有错误或无效。数据指定输入表单的错误字段。		
class APIValueError(APIError):
	def __init__(self,field,message = ''):
		super(APIValueError,self).__init__('value:invalid',field,message)

#表明没有找到资源。数据指定了资源名
class APIResourceNotFoundError(APIError):
	def __init__(self,field,message = ''):
		super(APIResourceNotFoundError,self).__init__('value:notfound',field,message)		
		
#表明接口没有权限
class APIPermissionError(APIError):
	def __init__(self,message = ''):
		super(APIPermissionError,self).__init__('permission:forbidden','permission',message)

'''if __name__=='__main__':
    import doctest
    doctest.testmod()
'''
