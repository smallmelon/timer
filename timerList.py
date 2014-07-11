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


def indexTv1(expires):
	return expires&TVR_MASK
def indexTv2(expires):
	return (expires>>TVR_BITS)&TVN_MASK
def indexTv3(expires):
	return (expires>>TVR_BITS + TVN_BITS*1)&TVN_MASK
def indexTv4(expires):
	return (expires>>TVR_BITS + TVN_BITS*2)&TVN_MASK
def indexTv5(expires):
	return (expires>>TVR_BITS + TVN_BITS*3)&TVN_MASK


if 'giKey' not in globals():
	giKey=0

class cTimerVec(object):
	def __init__(self,size):
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
		dVec=self.lVec[idx]
		for (expires,func,tArg,kArg) in dVec.itervalues():
			func(*tArg,**kArg)#运行函数
		self.lVec[idx]={}

	def move(self,idx):
		dVec=self.lVec[idx]
		self.lVec[idx]={}
		print 'move idx:{},dVec:{}'.format(idx,dVec)
		return dVec


class cTimerRoot(object):
	def __init__(self):
		self.jiffies=int(time.time())#单位s,或者在start的时候初始化
		self.tv1=cTimerVec(TVR_SIZE)
		self.tv2=cTimerVec(TVN_SIZE)
		self.tv3=cTimerVec(TVN_SIZE)
		self.tv4=cTimerVec(TVN_SIZE)
		self.tv5=cTimerVec(TVN_SIZE)
		gevent.spawn(self.__runTimer)

	def cascadeTimers(self,expires):
		if expires&TVR_MASK==0:#tv2
			dVec=self.tv2.move(indexTv2(expires))
			for iKey,(expires,func,tArg,kArg) in dVec.iteritems():
				self.addTimer2(iKey,expires,func,*tArg,**kArg)#重新加入
		if expires&MASK14==0:#tv3	
			dVec=self.tv3.move(indexTv3(expires))
			for iKey,(expires,func,tArg,kArg) in dVec.iteritems():
				self.addTimer2(iKey,expires,func,*tArg,**kArg)
		if expires&MASK20==0:#tv4
			dVec=self.tv4.move(indexTv4(expires))
			for iKey,(expires,func,tArg,kArg) in dVec.iteritems():
				self.addTimer2(iKey,expires,func,*tArg,**kArg)
		if expires&MASK26==0:#tv5
			dVec=self.tv5.move(indexTv5(expires))
			for iKey,(expires,func,tArg,kArg) in dVec.iteritems():
				self.addTimer2(iKey,expires,func,*tArg,**kArg)

	def findTimer(self,expires):
		idx=expires-self.jiffies
		if idx<0:
			return (None,0)
		if idx < TVR_SIZE:
			i=indexTv1(expires)
			return self.tv1,i
		elif idx < (1<<TVR_BITS+TVN_BITS):
			i=indexTv2(expires)
			return self.tv2,i
		elif idx < (1<<TVR_BITS+TVN_BITS*2):
			i=indexTv3(expires)
			return self.tv3,i
		elif idx < (1<<TVR_BITS+TVN_BITS*3):
			i=indexTv4(expires)
			return self.tv4,i
		elif idx < (1<<TVR_BITS+TVN_BITS*4):
			i=indexTv5(expires)
			return self.tv5,i

	def addTimer(self,expires,func,*tArg,**kArg):
		oTimer,idx=self.findTimer(expires)
		if not oTimer:
			raise Exception,'expires:{} is past time'.format(expires)
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
		expires=int(time.time())
		while True:
			#expires=int(time.time())
			idx=expires-self.jiffies
			if idx > 2:#相差应该在1s内的，超出应该就是出错了
				raise Exception,'now:{},rum timer have error,time interval more than 2 seconds'.format(expires)		
			self.cascadeTimers(expires)#刷新一下咯
			print 'now',expires
			self.tv1._runTimer(indexTv1(expires))
			gevent.sleep(0.001)#调试刷快1000速度
			expires=expires+1
			self.jiffies=expires

def test(s,t):
	print 'time:{},test:{}'.format(t-s,t)

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
