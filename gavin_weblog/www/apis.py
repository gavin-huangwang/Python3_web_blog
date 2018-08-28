# -*- coding: utf-8 -*-
#json api ����
import json,logging,inspect,functools


#��ʾҳ����࣬������������������ÿҳ�����ʾ���͵�ǰ��ʾ��ҳ���������ܹ��ж���ҳ�����·�ҳ
class Page(object):
	def __init__(self,item_count,page_index=1,page_size=10):	#ͨ����Ŀ������ҳ����������ҳ�����ߴ������з�ҳ��Page(101,10,10)��ʾ��101�����ݣ�ÿҳ���10�����ݣ���ʱչʾ���ǵ�10ҳ
		
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
		if (item_count ==0) or (page_index>page_count):		#��ʱ�����ݣ�չʾ��һҳ
			self.offset = 0	
			self.limit = 0
			self.page_index = 1
		else:
			self.offset = self.page_size*(page_index-1)		#ҳ��ƫ��������ʾ��ʾҳ��ӵڼ������ݿ�ʼ��ʾ��
			self.limit = self.page_size		#ÿҳ�������
			self.page_index = page_index
		self.has_next = self.page_index<self.page_count		#��һҳ��<������ƫ�Ʒ��ţ���ʾ�ӵ�ǰҳ�������ҳ��ƫ�ƣ�ÿ�μ�1
		self.has_previous = self.page_index>1		#��һҳ��>��ǰƫ��һλ
		
	def __str__(self):		#���ж���������print���õģ��Ὣ����ת��Ϊ�ַ��������print(Page)
		return 'item_count: %s, page_count: %s, page_index: %s, page_size: %s, offset: %s, limit: %s' % (self.item_count, self.page_count, self.page_index, self.page_size, self.offset, self.limit)
	
	__repr__ = __str__		#����������ʾ����Ϣ��print(Page)һ��	
		
#������APIError������������required�������ݣ�optional������Ϣ��optional��
class APIError(Exception):
	def __init__(self,error,data = '',message = ''):
		super(APIError,self).__init__(message)
		self.error = error
		self.data = data
		slef.message = message

#��ʾ����ֵ�д������Ч������ָ��������Ĵ����ֶΡ�		
class APIValueError(APIError):
	def __init__(self,field,message = ''):
		super(APIValueError,self).__init__('value:invalid',field,message)

#����û���ҵ���Դ������ָ������Դ��
class APIResourceNotFoundError(APIError):
	def __init__(self,field,message = ''):
		super(APIResourceNotFoundError,self).__init__('value:notfound',field,message)		
		
#�����ӿ�û��Ȩ��
class APIPermissionError(APIError):
	def __init__(self,message = ''):
		super(APIPermissionError,self).__init__('permission:forbidden','permission',message)

'''if __name__=='__main__':
    import doctest
    doctest.testmod()
'''
