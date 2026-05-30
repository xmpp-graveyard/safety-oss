"""
Module "ithr" (for Python 2.6+)
ithr.py

Partial copyright (2010-2013) Al Korgun (alkorgun@gmail.com)

Distributed under the PSFL.
"""

import sys

try:
	import thread
except ImportError:
	del sys.modules[__name__]
	raise

from traceback import format_exc as get_exc

sThread_Run = thread.start_new_thread
get_ident = thread.get_ident
allocate_lock = thread.allocate_lock
stack_size = thread.stack_size
error = thread.error

del thread

import time
import warnings

__all__ = [
	"BoundedSemaphore",
	"Condition",
	"Event",
	"KThread",
	"Number",
	"PickSomeNonDaemonThread",
	"RLock",
	"Semaphore",
	"Thread",
	"Timer",
	"UnBoundedSemaphore",
	"allocate_lock",
	"currentThread",
	"enumerate",
	"error",
	"get_exc",
	"get_ident",
	"getNames",
	"killAllThreads",
	"sThread_Run",
	"stack_size"
]

__version__ = "1.5"

warnings.filterwarnings("ignore", category = DeprecationWarning, module = __name__, message = "sys.exc_clear")

class RLock(object):

	def __init__(self, object = None):
		self.__block = allocate_lock()
		self.__owner = None
		self.__count = 0

	def __repr__(self):
		owner = self.__owner
		try:
			owner = ActiveThreads[owner].name
		except KeyError:
			pass
		return "<%s owner=%r count=%d>" % (self.__class__.__name__, owner, self.__count)

	def acquire(self, blocking = 1):
		me = get_ident()
		if self.__owner is me:
			self.__count += 1
			return 1
		rc = self.__block.acquire(blocking)
		if rc:
			self.__owner = me
			self.__count = 1
		return rc

	__enter__ = acquire

	def release(self):
		if self.__owner != get_ident():
			raise RuntimeError("cannot release un-acquired lock")
		self.__count -= 1
		if not count:
			self.__owner = None
			self.__block.release()

	def __exit__(self, *args):
		self.release()

	def _acquire_restore(self, count_owner):
		count, owner = count_owner
		self.__block.acquire()
		self.__count = count
		self.__owner = owner

	def _release_save(self):
		count = self.__count
		self.__count = 0
		owner = self.__owner
		self.__owner = None
		self.__block.release()
		return (count, owner)

	def _is_owned(self):
		return (self.__owner is get_ident())

class Condition(object):

	def __init__(self, lock = None, object = None):
		if lock is None:
			lock = RLock()
		self.__lock = lock
		self.acquire = lock.acquire
		self.release = lock.release
		if hasattr(self.__lock, "locked"):
			self.release = self.secure_release
		if hasattr(self.__lock, "_release_save"):
			self._release_save = self.__lock._release_save
		if hasattr(self.__lock, "_acquire_restore"):
			self._acquire_restore = self.__lock._acquire_restore
		if hasattr(self.__lock, "_is_owned"):
			self._is_owned = self.__lock._is_owned
		self.__waiters = []

	def __enter__(self):
		return self.__lock.__enter__()

	def __exit__(self, *args):
		return self.__lock.__exit__(*args)

	def __repr__(self):
		return "<Condition(%s, %d)>" % (self.__lock, len(self.__waiters))

	def _release_save(self):
		self.__lock.release()

	def _acquire_restore(self, x):
		self.__lock.acquire()

	def _is_owned(self):
		if self.__lock.acquire(0):
			self.__lock.release()
			return False
		return True

	def secure_release(self):
		if self.__lock.locked():
			self.__lock.release()

	def wait(self, timeout = None):
		if not self._is_owned():
			raise RuntimeError("cannot wait on un-acquired lock")
		waiter = allocate_lock()
		waiter.acquire()
		self.__waiters.append(waiter)
		saved_state = self._release_save()
		try:
			if timeout is None:
				waiter.acquire()
			else:
				endtime = (time.time() + timeout)
				delay = 0.0005
				while True:
					gotit = waiter.acquire(0)
					if gotit:
						break
					remaining = (endtime - time.time())
					if remaining <= 0:
						break
					delay = min(delay * 2, remaining, 0.05)
					time.sleep(delay)
				if not gotit:
					try:
						self.__waiters.remove(waiter)
					except ValueError:
						pass
		finally:
			self._acquire_restore(saved_state)

	def notify(self, number = 1):
		if not self._is_owned():
			raise RuntimeError("cannot notify on un-acquired lock")
		__waiters = self.__waiters
		waiters = __waiters[:number]
		if not waiters:
			return
		for waiter in waiters:
			waiter.release()
			try:
				__waiters.remove(waiter)
			except ValueError:
				pass

	def notify_all(self):
		self.notify(len(self.__waiters))

class Semaphore(object):

	def __init__(self, value = 1, object = None):
		if value < 0:
			raise ValueError("semaphore initial value must be >= 0")
		self.__cond = Condition(allocate_lock())
		self.__value = value

	def acquire(self, blocking = 1):
		rc = False
		self.__cond.acquire()
		while self.__value is 0:
			if not blocking:
				break
			self.__cond.wait()
		else:
			self.__value -= 1
			rc = True
		self.__cond.release()
		return rc

	__enter__ = acquire

	def release(self):
		self.__cond.acquire()
		self.__value += 1
		self.__cond.notify()
		self.__cond.release()

	def __exit__(self, *args):
		self.release()

class BoundedSemaphore(Semaphore):

	def __init__(self, value = 1):
		Semaphore.__init__(self, value)
		self.basic_value = value

	def release(self):
		if self.__value >= self.basic_value:
			raise ValueError("Semaphore released too many times")
		return Semaphore.release(self)

class UnBoundedSemaphore(Semaphore):

	def __init__(self, value = 1):
		Semaphore.__init__(self, value)
		self.basic_value = value
		self.acquire.__func__.func_defaults = (0,)

	def release(self):
		self.__cond.acquire()
		if self.__value < self.basic_value:
			self.__value += 1
		self.__cond.notify()
		self.__cond.release()

class Event(object):

	def __init__(self, object = None):
		self.__cond = Condition(allocate_lock())
		self.__flag = False

	def isSet(self):
		return self.__flag

	def set(self):
		self.__cond.acquire()
		try:
			self.__flag = True
			self.__cond.notify_all()
		finally:
			self.__cond.release()

	def clear(self):
		self.__cond.acquire()
		try:
			self.__flag = False
		finally:
			self.__cond.release()

	def wait(self, timeout = None):
		self.__cond.acquire()
		try:
			if not self.__flag:
				self.__cond.wait(timeout)
			return self.__flag
		finally:
			self.__cond.release()

try:
	from itypes import Number
except ImportError:

	class Number(object):

		def __init__(self, number = int()):
			self.number = number

		def plus(self, number = 0x1):
			self.number += number
			return self.number

		def reduce(self, number = 0x1):
			self.number -= number
			return self.number

		__int__ = lambda self: self.number.__int__()

		_int = lambda self: self.__int__()

		__str__ = __repr__ = lambda self: self.number.__repr__()

		_str = lambda self: self.__str__()

Counter, aCounter = Number(), Number()

_newname = lambda template = "Thread-%d": template % (aCounter._int() + 1)

active_limbo_lock = allocate_lock()
ActiveThreads = {}
Thrlimbo = {}

class Thread(object):

	__initialized = False

	def __init__(self, group = None, target = None, name = None, args = (), kwargs = None, object = None):
		assert group is None, "group argument must be None for now"
		if kwargs is None:
			kwargs = {}
		self.__target = target
		self.__name = str(name or _newname())
		self.__limbo_name = aCounter.plus()
		self.__args = args
		self.__kwargs = kwargs
		self.__daemonic = self._set_daemon()
		self.__ident = None
		self.__started = Event()
		self.__stopped = False
		self.__block = Condition(allocate_lock())
		self.__initialized = True
		self.__stderr = sys.stderr

	def _set_daemon(self):
		return currentThread().daemon

	def __repr__(self):
		assert self.__initialized, "Thread.__init__() was not called"
		status = "initial"
		if self.__started.isSet():
			status = "started"
		if self.__stopped:
			status = "stopped"
		if self.__daemonic:
			status += " daemon"
		if self.__ident is not None:
			status += " %s" % self.__ident
		return "<%s(%s, %s)>" % (self.__class__.__name__, self.__name, status)

	def start(self):
		if not self.__initialized:
			raise RuntimeError("thread.__init__() not called")
		if self.__started.isSet():
			raise RuntimeError("threads can only be started once")
		with active_limbo_lock:
			Thrlimbo[self.__limbo_name] = self
		try:
			sThread_Run(self.__bootstrap, ())
		except Exception:
			with active_limbo_lock:
				del Thrlimbo[self.__limbo_name]
			raise
		self.__started.wait()

	def run(self):
		Counter.plus()
		try:
			if self.__target:
				self.__target(*self.__args, **self.__kwargs)
		finally:
			del self.__target, self.__args, self.__kwargs

	def __bootstrap(self):
		try:
			self.__bootstrap_inner()
		except SystemExit:
			pass
		except KeyboardInterrupt:
			pass
		except Exception:
			if self.__daemonic and sys is None:
				return None
			raise

	def _set_ident(self):
		self.__ident = get_ident()

	def __bootstrap_inner(self):
		try:
			self._set_ident()
			self.__started.set()
			with active_limbo_lock:
				ActiveThreads[self.__ident] = self
				try:
					del Thrlimbo[self.__limbo_name]
				except KeyError:
					pass
			try:
				self.run()
			except SystemExit:
				pass
			except KeyboardInterrupt:
				pass
			except Exception:
				try:
					sys.stderr.write("Exception in thread %s:\n%s\n" % (self.name, get_exc()))
				except Exception:
					pass
			finally:
				sys.exc_clear()
		finally:
			with active_limbo_lock:
				self.__stop()
				try:
					del ActiveThreads[get_ident()]
				except Exception:
					pass

	def __stop(self):
		self.__block.acquire()
		self.__stopped = True
		self.__block.notify_all()
		self.__block.release()

	def __delete(self):
		with active_limbo_lock:
			try:
				del ActiveThreads[get_ident()]
			except KeyError:
				if not sys.modules.has_key("dummy_threading"):
					raise

	def join(self, timeout = None):
		if not self.__initialized:
			raise RuntimeError("Thread.__init__() not called")
		if not self.__started.isSet():
			raise RuntimeError("cannot join thread before it is started")
		if self is currentThread():
			raise RuntimeError("cannot join current thread")
		self.__block.acquire()
		try:
			if timeout is None:
				while not self.__stopped:
					self.__block.wait()
			else:
				deadline = time.time() + timeout
				while not self.__stopped:
					delay = deadline - time.time()
					if delay <= 0:
						break
					self.__block.wait(delay)
		finally:
			self.__block.release()

	@property
	def name(self):
		assert self.__initialized, "Thread.__init__() not called"
		return self.__name

	@name.setter
	def name(self, name):
		assert self.__initialized, "Thread.__init__() not called"
		self.__name = str(name)

	@property
	def ident(self):
		assert self.__initialized, "Thread.__init__() not called"
		return self.__ident

	def isAlive(self):
		assert self.__initialized, "Thread.__init__() not called"
		return self.__started.isSet() and not self.__stopped

	@property
	def daemon(self):
		assert self.__initialized, "Thread.__init__() not called"
		return self.__daemonic

	@daemon.setter
	def daemon(self, daemonic):
		if not self.__initialized:
			raise RuntimeError("Thread.__init__() not called")
		if self.__started.isSet():
			raise RuntimeError("cannot set daemon status of active thread")
		self.__daemonic = daemonic

	def isDaemon(self):
		return self.daemon

	def setDaemon(self, daemonic):
		self.daemon = daemonic

	def getName(self):
		return self.name

	def setName(self, name):
		self.name = name

class ThrKill(SystemExit):
	pass

class KThread(Thread): # by Connelly Barnes (connellybarnes@yahoo.com)

	def __init__(self, *args, **kwargs):
		Thread.__init__(self, None, *args, **kwargs)
		self.killed = False
		self._run_backup = self.run
		self.run = self.__run
		self._start_backup = self.start
		self.start = self.__start

	def __run(self):
		sys.settrace(self.globaltrace)
		try:
			self._run_backup()
		except ThrKill:
			pass

	def __start(self):
		try:
			self._start_backup()
		except ThrKill:
			pass

	def globaltrace(self, frame, why, arg):
		if why == "call":
			return self.localtrace
		return None

	def localtrace(self, frame, why, arg):
		if self.killed:
			if why == "line":
				raise ThrKill("exit")
		return self.localtrace

	def kill(self):
		self.killed = True

class Timer(Thread):

	def __init__(self, interval, function, args = (), kwargs = {}):
		Thread.__init__(self)
		self.interval = interval
		self.function = function
		self.args = args
		self.kwargs = kwargs
		self.finished = Event()

	def cancel(self):
		self.finished.set()

	def kill(self):
		self.cancel()

	def run(self):
		Counter.plus()
		self.finished.wait(self.interval)
		if not self.finished.isSet():
			self.function(*self.args, **self.kwargs)
		self.finished.set()

class MainThread(Thread):

	def __init__(self):
		Thread.__init__(self, name = "MainThread")
		self._Thread__started.set()
		self._set_ident()
		with active_limbo_lock:
			ActiveThreads[get_ident()] = self

	def _set_daemon(self):
		return False

	def kill(self):
		pass

	def _exitfunc(self):
		self._Thread__stop()
		thr = PickSomeNonDaemonThread()
		while thr:
			thr.join()
			thr = PickSomeNonDaemonThread()
		self._Thread__delete()

def PickSomeNonDaemonThread():
	for thr in enumerate():
		if not thr.daemon and thr.isAlive():
			return thr
	return None

class DummyThread(Thread):

	def __init__(self):
		Thread.__init__(self, name = _newname("Dummy-%d"))
		del self._Thread__block
		self._Thread__started.set()
		self._set_ident()
		with active_limbo_lock:
			ActiveThreads[get_ident()] = self

	def _set_daemon(self):
		return True

	def kill(self):
		pass

	def join(self, timeout = None):
		assert False, "cannot join a dummy thread"

def currentThread():
	ident = get_ident()
	if ident in ActiveThreads:
		thr = ActiveThreads[ident]
	else:
		thr = DummyThread()
	return thr

def enumerate():
	with active_limbo_lock:
		return (ActiveThreads.values() + Thrlimbo.values())

getNames = lambda: [thr.name for thr in enumerate()]

def killAllThreads():
	for thr in enumerate():
		if thr.ident != get_ident():
			thr.kill()

_shutdown = MainThread()._exitfunc

def _after_fork():
	global active_limbo_lock
	active_limbo_lock = allocate_lock()
	ActiveNew = {}
	current = currentThread()
	with active_limbo_lock:
		for thr in ActiveThreads.itervalues():
			if thr is current:
				thr._Thread__ident = get_ident()
				ActiveNew[thr._Thread__ident] = thr
			else:
				thr._Thread__stopped = True
		Thrlimbo.clear()
		ActiveThreads.clear()
		ActiveThreads.update(ActiveNew)
		assert len(ActiveThreads) == 1
