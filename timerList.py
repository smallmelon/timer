#-*-coding:utf-8-*-
#email:myfishlgc@163.com

import gevent

TVN_BITS=6
TVR_BITS=8
TVN_SIZE=1<<TVN_BITS
TVR_SIZE=1<<TVR_BITS
TVR_MASK=(TVR_SIZE - 1)
TVN_MASK=(TVN_SIZE - 1)
MASK14=(1<<(TVR_BITS+TVN_BITS*1)) - 1
MASK20=(1<<(TVR_BITS+TVN_BITS*2)) - 1 
MASK26=(1<<(TVR_BITS+TVN_BITS*3)) - 1


if 'giKey' not in globals():
	giKey=0

class cTimerVec(object):
	def __init__(self,size):
		self.iIdx=0
		self.size=size
		self.lVec=[{} for i in range(size)]
	#有没有必要返回一个索引值，方便他删除呢？
	#非常有必要！
	
	def addTimer(self,idx,expires,func,*tArg,**kArg):#先这样子吧，以后做成闭包
		dVec=self.lVec[idx]
		global giKey
		giKey+=1
		dVec[giKey]=(expires,func,tArg,kArg)
		return giKey

	def addTimer2(self,idx,iKey,expires,func,*tArg,**kArg):#先这样子吧，以后做成闭包
		dVec=self.lVec[idx]
		dVec[iKey]=(expires,func,tArg,kArg)

	def removeTimer(self,idx,iKey):#idx有可能过时了?
		dVec=self.lVec[idx]
		dVec.pop(iKey,None)

	def _runTimer(self,idx):#实际上只有一个定时器会调用这个函数t 
		self.iIdx
		dVec=self.lVec[idx]
		for (expires,func,tArg,kArg) in dVec.itervalues():
			func(*tArg,**kArg)#运行函数
		self.lVec[idx]={}
		self.idx=(self.iIdx+1)&(self.size-1)

	def move(self):
		dVec=self.lVec[self.iIdx]
		self.lVec[self.iIdx]={}
		self.iIdx=(self.iIdx+1)&(self.size-1)
		return dVec


class cTimerRoot(object):
	def __init__(self):
		self.tv1=cTimerVec(TVR_SIZE)
		self.tv2=cTimerVec(TVN_SIZE)
		self.tv3=cTimerVec(TVN_SIZE)
		self.tv4=cTimerVec(TVN_SIZE)
		self.tv5=cTimerVec(TVN_SIZE)
		self.jiffies=int(time.time())#单位s,或者在start的时候初始化
		gevent.spawn(self.__runTimer)

	def cascadeTimers(self,expires):
		print 'tv2  %x' % (expires&TVR_MASK)
		if expires&TVR_MASK==0:#tv2
			print 'tv2'
			dVec=self.tv2.move()
			for iKey,(expires,func,tArg,kArg) in dVec.iteritems():
				self.addTimer2(iKey,expires,func,tArg,kArg)#重新加入
		print 'tv3  %x' % (expires&MASK14)
		if expires&MASK14==0:#tv3	
			dVec=self.tv3.move()
			for iKey,(expires,func,tArg,kArg) in dVec.iteritems():
				self.addTimer2(iKey,expires,func,tArg,kArg)
		print 'tv4 %x' % (expires&MASK20)
		if expires&MASK20==0:#tv4
			dVec=self.tv4.move()
			for iKey,(expires,func,tArg,kArg) in dVec.iteritems():
				self.addTimer2(iKey,expires,func,tArg,kArg)
		print 'tv5 %x' % (expires&MASK26)
		if expires&MASK26==0:#tv5
			dVec=self.tv5.move()
			for iKey,(expires,func,tArg,kArg) in dVec.iteritems():
				self.addTimer2(iKey,expires,func,tArg,kArg)

	def findTimer(self,expires):
		idx=expires-self.jiffies
		if idx<0:
			return (None,0)
		if idx < TVR_SIZE:
			i=expires&TVR_MASK
			return self.tv1,i
		elif idx < (1<<TVR_BITS+TVN_BITS):
			i=(expires>>TVR_BITS)&TVN_MASK
			return self.tv2,i
		elif idx < (1<<TVR_BITS+TVN_BITS*2):
			i=(expires>>(TVR_BITS+TVN_BITS*1))&TVN_MASK
			return self.tv3,i
		elif idx < (1<<TVR_BITS+TVN_BITS*3):
			i=(expires>>(TVR_BITS+TVN_BITS*2))&TVN_MASK
			return self.tv4,i
		elif idx < (1<<TVR_BITS+TVN_BITS*4):
			i=(expires>>(TVR_BITS+TVN_BITS*3))&TVN_MASK
			return self.tv5,i

	def addTimer(self,expires,func,*tArg,**kArg):
		oTimer,idx=self.findTimer(expires)
		if not oTimer:
			raise Exception,'expires:{} is past time'.format(expires)
		'addTimer',idx
		return oTimer.addTimer(idx,expires,func,*tArg,**kArg)
	
	def addTimer2(self,iKey,expires,func,*tArg,**kArg):#重新加入
		oTimer,idx=self.findTimer(expires)
		if not oTimer:
			raise Exception,'expires:{} is past time'.format(expires)
		return oTimer.addTimer2(idx,iKey,expires,func,*tArg,**kArg)
	

	def removeTimer(self,expires,iKey):
		oTimer,idx=self.findTimer(iKey)
		if not oTimer:
			raise Exception,'expires:{} is past time'.format(expires)
		oTimer.removeTimer(idx,iKey)

	def __runTimer(self):
		while True:
			gevent.sleep(1)#定时1s
			expires=int(time.time())
			idx=expires-self.jiffies
			if idx > 2:#相差应该在1s内的，超出应该就是出错了
				raise Exception,'now:{},rum timer have error,time interval more than 2 seconds'.format(expires)		
			i=expires&TVR_MASK
			self.tv1._runTimer(i)
			self.cascadeTimers(expires)#刷新一下咯
			self.jiffies=expires

def test(s,t):
	print 'time:{},expires:{}'.format(t-s,s)

import sys
import time
if __name__ == '__main__':
	oTimer=cTimerRoot()
	end=int(sys.argv[1])
	expires=int(time.time())
	for i in xrange(1,end,1):
		oTimer.addTimer(expires+i,test,expires,expires+i)
		#oTimer.addTimer(expires+i,test,expires,expires+i+1)
		#oTimer.addTimer(expires+i,test,expires,expires+i+2)
		#oTimer.addTimer(expires+i,test,expires,expires+i+3)
	gevent.wait()



