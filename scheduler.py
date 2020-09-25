import time
import threading

class scheduler:
	def __init__(self,name = 'default'):
		self.name = name
		self.everies= []

	def add_every(self,interval = 1, unit = 'second',conditions = [],function = None, name = 'default'):
		self.everies.append(every(interval,unit,conditions,function,name))
		

	
class every:
	def __init__(self,interval = 1, unit = 'second',conditions = [], function = None,name='default',args = (), kwargs = {},maximum_nexecuters=10,verbose = False):
		self.verbose = verbose
		self.running = False
		self.interval = interval
		self.unit2seconds = make_unit2seconds()
		if not unit in self.unit2seconds.keys():
			print(unit,'not recognized, using default: seconds')
			unit = 'second'
		self.unit = unit
		self.conditions = conditions
		self.interval_seconds = self.interval * self.unit2seconds[unit]
		if function == None: self.function = self.set_interval_reached()
		self.function = function
		self.name = name
		self.args = args
		self.kwargs = kwargs
		self.executers = []
		self.maximum_nexecuters = maximum_nexecuters
		self.ninterval = 0
		self.interval_reached = False

	def set_interval_reached(self):
		print(self.interval,'interval reached')

	def check_conditions(self):
		if len(self.conditions) > 2: print('probably to many conditions',self.condtions)
		if len(self.conditions) == 2 and 'weekday' not in self.conditions and 'weekend' not in self.conditions: print('multiple conditions should contain weekend or weekday',self.conditions)
		self.seconds_to_conditions_met = 0
		for condition in self.conditions:
			if time2(condition) > self.seconds_to_conditions_met:self.seconds_to_conditions_met = time2(condition)
		if self.seconds_to_conditions_met == 0: self.conditions_met = True
		else: self.conditions_met = False
		if self.verbose:
			print('seconds to conditions met:',self.seconds_to_conditions_met,'conditions:',self.conditions)

	def run(self):
		self.running = True
		self.check_conditions()
		self.remove_finished_executers()
		if not self.conditions_met: 
			print('waiting for conditions to be met:',self.conditions,self.seconds_to_conditions_met)
			# self.wait(int(self.seconds_to_conditions_met/100))
			self.wait(10)
		elif len(self.executers) >= self.maximum_nexecuters:
			print('waiting to execute funciton, maximum nexecuters is reached:',self.maximum_nexecuters)
			self.wait(1)
		else:
			if self.verbose:
				print('executing function:',self.function,'if none setting interval_reached to true.')
			self.execute()

	def stop(self):
		self.waiter.cancel()
		self.executers = []
		self.running = False

	def wait(self,wait):
		self.waiter = threading.Timer(wait,self.run)
		self.waiter.start()

	def execute(self):
		e = threading.Thread(target= self.function,args=self.args,kwargs=self.kwargs) 
		e.start()
		self.executers.append(e)
		self.wait(self.interval_seconds)

	def remove_finished_executers(self):
		temp = []
		for executer in self.executers:
			if executer.is_alive():
				temp.append(executer)
		self.executers = temp

		
def make_unit2seconds():
	day = 24*3600
	return {'second':1,'minute':60,'hour':3600,'day':day,'week':7*day,'month':30*day,'year':365*day}



def get_dayname(t = None):
	if t == None: t = time.time()
	return time.strftime('%A', time.localtime(t))

def is_day_of_week(name,t= None):
	if t == None: t = time.time()
	return name == time.strftime('%A', time.localtime(t))

	

def is_weekend(t = None):
	if t == None: t = time.time()
	if get_dayname(t) in ['Saturday','Sunday']: return True
	else: return False

def is_weekday(t = None):
	if t == None: t = time.time()
	return not is_weekend(t)

def is_day(t = None):
	if t == None: t = time.time()
	h = int(time.strftime('%H%M', time.localtime(t)))
	if h >= 600 and h < 1800: return True 
	else: return False

def is_officehours(t = None):
	if t == None: t = time.time()
	h = int(time.strftime('%H%M', time.localtime(t)))
	if is_weekend(t): return False
	if h >= 900 and h < 1700: return True 
	else: return False

def is_leisuretime(t=None):
	if t == None: t = time.time()
	if is_weekend(t) or not is_officehours(t): return True
	return False

def is_night(t = None):
	if t == None: t = time.time()
	return not is_day(t)

def is_morning(t = None):
	if t == None: t = time.time()
	h = int(time.strftime('%H%M', time.localtime(t)))
	if h >= 600 and h < 1200: return True
	else: return False

def is_afternoon(t = None):
	if t == None: t = time.time()
	h = int(time.strftime('%H%M', time.localtime(t)))
	if h >= 1200 and h < 1800: return True
	else: return False

def is_evening(t = None):
	if t == None: t = time.time()
	h = int(time.strftime('%H%M', time.localtime(t)))
	if h >= 1800: return True
	else: return False
	
def is_deepnight(t = None):
	if t == None: t = time.time()
	h = int(time.strftime('%H%M', time.localtime(t)))
	if h < 600: return True
	else: return False

def is_between(start,end, t = None):
	if t == None: t = time.time()
	h = int(time.strftime('%H%M', time.localtime(t)))
	if start < end: return h >= start and h < end
	else: return h >= start or h < end

# Time to functions

def h2s(h):
	if len(str(h)) > 2: return int(h/100) * 3600 + h%100 * 60
	else: return h * 60 

def s2h(s):
	h = int(s/3600) * 100
	s = s%3600
	h += int(s/60)
	return h

def make_weekday_names2n():
	return {'Sunday':0,'Monday':1,'Tuesday':2,'Wednesday':3,'Thursday':4,'Friday':5,'Saturday':6}

def time2(moment = 'day',t = None):
	if t == None: t = time.time()
	weekday_names2n = make_weekday_names2n()
	h = int(time.strftime('%H%M', time.localtime(t)))
	s = h2s(h)
	if moment == 'day':
		if is_day(t): return 0
		if h >= 1800: rs = h2s(3000) - s
		else: rs = h2s(600) - s
	elif moment == 'night':
		if is_night(t): return 0
		rs = h2s(1800) - s
	elif moment == 'morning':
		if is_morning(t): return 0
		if h >= 1200: rs = h2s(3000) - s
		else: rs = h2s(600) - s
	elif moment == 'afternoon':
		if is_afternoon(t): return 0
		if h >= 1800: rs = h2s(3600) - s
		else: rs = h2s(1200) - s
	elif moment == 'evening':
		if is_evening(t): return 0
		rs = h2s(1800) - s
	elif moment == 'deepnight' or moment == 'tomorrow':
		if is_deepnight(t): return 0
		rs = h2s(2400) - s
	elif moment == 'officehours':
		if is_officehours(t): return 0
		if is_weekday():
			if h >= 1700: 
				if get_dayname(t) != 'Friday': rs = h2s(3300) - s
				else: rs = h2s(8100) - s
			else: rs = h2s(900) - s
		else: rs = time2('weekday',t) + 900
	elif moment == 'leisuretime':
		if is_leisuretime(t): return 0
		rs = h2s(1700) - s
	elif moment == 'weekday':
		if is_weekday(t): return 0
		if get_dayname(t) == 'Saturday': rs = h2s(4800) - s 
		else: rs = h2s(2400) - s 
	elif moment == 'weekend':
		if is_weekend(t): return 0
		day_number = int(time.strftime('%w', time.localtime(t)))	
		rs = h2s((6 - day_number) * 2400) - s
	elif moment in weekday_names2n.keys():
		tname = time.strftime('%A', time.localtime(t))
		if tname == moment: return 0
		tnumber = weekday_names2n[tname] + 1
		namenumber = weekday_names2n[moment] + 1 
		if namenumber<tnumber: dif = 7 - namenumber - 1
		else: dif = namenumber - tnumber - 1
		print(dif,tnumber,namenumber)
		rs = h2s(dif * 2400) + h2s(2400) - s
	elif type(moment) == tuple and len(moment) == 2 and type(moment[0]) == int:
		start, end = moment
		if is_between(start,end,t): return 0
		if end > start and h >= end: rs = h2s(2400 + start) - s
		else: rs = h2s(start) - s
	else:
		print(moment, 'is not defined, return 0')
	return rs

def print_time():
	time.sleep(6)
	print('time is now:',int(time.strftime('%H%M', time.localtime(time.time()))),time.time())



	
	

