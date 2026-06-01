# coding: utf-8

import time
import logging
import os

if os.path.exists("BlackSmith.py"):
	from __main__ import *
else:
	from BlackSmith import *

from copy import deepcopy

LOG_LEVEL = logging.DEBUG
logFile = "vercheck.log"

vercheck_logger = logging.getLogger("vercheck")
vercheck_logger.setLevel(LOG_LEVEL)
vercheck_loggerHandler = logging.FileHandler(logFile)
formatter = logging.Formatter("%(asctime)s %(levelname)s:"
	"%(name)s: %(message)s", "%d.%m.%Y %H:%M:%S")
vercheck_loggerHandler.setFormatter(formatter)
vercheck_logger.addHandler(vercheck_loggerHandler)

from writer import *
from printer import *
from utils import *

# config
USERNAME = ""
PASSWORD = ""
RESOURCE = ""
NICKNAME = ""
SERVER = "matrix.bz"
USE_SEPARATE_CLIENT = False


class NoFreeHands(Exception):
	pass


class QueueDisabled(Exception):
	pass


def getJid(client):
	return "%s@%s" % (client._owner.User, client._owner.Server)


def execute(handler, list=()):
	"""
	Just executes handler(*list) safely
	If weird error is happened writes a crashlog
	"""
	try:
		result = handler(*list) or 0
	except (SystemExit, xmpp.NodeProcessed):
		result = 1
	except Exception:
		result = -1
		crashLog(handler.func_name)
	return result


def runThread(func, args=(), name=None, att=3, delay=0):
	if delay:
		thr = threading.Timer(delay, execute, (func, args))
	else:
		thr = threading.Thread(target=execute, args=(func, args))
	name = name or func.__name__
	name = str(name) + "-" + str(time.time())
	thr.name = name
	try:
		thr.start()
	except (threading.ThreadError):
		if att:
			return runThread(func, args, name, (att - 1), delay)


def threaded(func):
	"""
	Another decorator.
	Executes a function in a thread
	"""
	def wrapper(*args):
		runThread(func, args)
		return True
	wrapper.__name__ = "threaded_%s" % func.__name__
	return wrapper


def safe_kwargs(func):
	"""
	A decorator.
	Executes func(*args) safely
	"""
	def wrapper(*args, **kwargs):
		try:
			func(*args, **kwargs)
		except Exception:
			crashLog(func.func_name)
	wrapper.__name__ = func.__name__
	return wrapper


class Child(object):

	def __init__(self, username, server, password, nick):
		self.username = username
		self.password = password
		self.server = server
		self.port = 5222
		self.disp = xmpp.Client(server, self.port, debug=[])
		self.nick = nick
		self.status = "I'm just a child of Safety."

	def connect(self, secure=None):
		self.connected = connected = self.disp.connect((self.server, self.port), secure=secure)
		vercheck_logger.debug("connect" + ("ed" if connected else " failed"))
		return self

	def auth(self, resource=RESOURCE):
		self.authenticated = authenticated = self.disp.auth(self.username, self.password, resource)
		vercheck_logger.debug("auth" + ("enticated" if authenticated else "entication failed"))
		return self

	@threaded
	def finish(self):
		# IQCB!!!
		if self.connected and self.authenticated:
			self.alive_keeper()
			self.dispatcher()
		else:
			time.sleep(1)
			self.finish()

	def getDisp(self, disp=None):
		if self.connected and self.authenticated:
			return self.disp
		vercheck_logger.error("Child's disp isn't connected! Using bot's own disp")
		return disp

	def sender(self, stanza, cb=None, args={}):
		if cb:
			self.disp.SendAndCallForResponse(stanza, cb, args)
		else:
			try:
				self.disp.send(stanza)
			except Exception:
				vercheck_logger.critical("Exception happened while sending stanza! %s" % traceback.format_exc())
				self.restart()

	@threaded
	def alive_keeper(self):

		def alive_keeper_answer(disp, stanza):
			disp.aKeeper = 0

		while self.disp.isConnected():
			time.sleep(60)
			if not hasattr(self.disp, "aKeeper"):
				self.disp.aKeeper = 0

			if self.disp.aKeeper > 5:
				Print("No answer from the server, restarting...")
				self.restart()
			else:
				self.disp.aKeeper += 1
				iq = xmpp.Iq("get", to="%s@%s/%s" % (USERNAME, SERVER, RESOURCE))
				iq.addChild("ping", namespace=xmpp.NS_PING)
				self.sender(iq, cb=alive_keeper_answer)

	@threaded
	def dispatcher(self):
		while self.disp.isConnected():
			self.disp.Process(5)


class ArrayList(object):

	def __init__(self):
		self.values = [0, 0]

	def sort(self):
		"""
		Sorts incorrectly placed values
		[float, int] -> [int, float]
		"""
		output = self.values
		if len(self.values) > 0:
			if not isinstance(self.values[1], float):
				if isinstance(self.values[0], float):
					output = [values[1], values[0]]
		self.values = output

	def add(self, value):
		if isinstance(value, float):
			self.values[0] = value
		elif isinstance(value, int):
			self.values[1] = value
		return self

	def plus(self):
		self.add(self.values[1] + 1)
		return self

	def minus(self):
		self.add(self.values[1] - 1 if self.values[1] > 0 else 0)
		return self

	def addTimeStamp(self):
		self.add(time.time())
		return self

	def getTimeStamp(self):
		return self.values[0]

	def getBusy(self):
		return self.values[1]


def restartOnFail(func):
	"""
	Restarts a specific function if it fails
	"""
	def wrapper(*args):
		try:
			func(*args)
		except Exception:
			vercheck_logger.error("function %s just failed! Traceback: %s", func.func_name, traceback.format_exc())
			func(*args)
	wrapper.__name__ = func.func_name
	return wrapper


class LoadBalancer(object):
	def __init__(self):
		self.clients = {}  # jid -> ArrayList()
		self.MAX_PENDING = 10
		self.balancing = True
		self.USE_QUEUE = True  # can be false
		self.EXPIRY_TIME = 60  # sixty seconds
		self.operations = []

	def disableQueue(self):
		self.USE_QUEUE = False

	def enableQueue(self):
		# start queue thread here
		self.USE_QUEUE = True
		self.queueWorker()

	@threaded
	@restartOnFail
	def expWorker(self):
		while self.balancing:
			for val in self.clients.itervalues():
				list = self.clients.get(val)  #
				if list:
					if (time.time() - list[0]) >= self.EXPIRY_TIME:
						list.minus().addTimeStamp()
			time.sleep(1)

	@threaded
	def queueWorker(self):
		while self.USE_QUEUE:
			if self.hasFreeHands(disp):
				self.run(*self.operations.pop(0))
			time.sleep(1)

	def getList(self, disp):
		jid = disp
		if isinstance(disp, xmpp.client.Client):
			jid = getJid(disp)
		if jid in self.clients:
			return self.clients[jid]
		return ArrayList()  # Empty ArrayList shouldn't make any sense

	def add(self, disp):
		jid = getJid(disp)
		if jid not in self.clients:
			self.clients[jid] = ArrayList()
		self.clients[jid].addTimeStamp().plus()
		return self

	def free(self, disp):
		list = self.getList(self, disp)
		list.minus()

	def hasFreeHands(self, disp):
		list = self.getList(disp)
		if list.getBusy() <= self.MAX_PENDING:
			return True
		return False

	@threaded
	def run(self, disp, func, iq, args):
		args["callback"] = self.free
		disp.SendAndCallForResponse(iq, func, args)

	def queue(self, func, disp, iq, args):
		self.add(disp)
		if self.hasFreeHands(disp):
			self.run(disp, func, iq, args)
		elif self.USE_QUEUE:
			self.operations.append([disp, func, iq, args])


Balancer = LoadBalancer()


class expansion_temp(expansion):
	actions = ["filter", "ban", "kick", "visitor"]
	defaults = {"limit": 0, "data": {"name": [], "os": []}, "enabled": False}
	client = None
	onResult = {}
	Config = {}
	ConfFile = "vercheck.base"

	def __init__(self, name):
		expansion.__init__(self, name)

	def version_check(self, chat, disp, nick, jid, res):
		# TODO: the code below might be useful when the user actually joined the chat
		# if USE_SEPARATE_CLIENT:
		# 	to = "%s/%s" % (jid, res)
		# else:
		# 	to = "%s/%s" % (chat, nick)
		to = "%s/%s" % (jid, res)
		iq = xmpp.Iq("get", to=to)
		iq.addChild("query", namespace=xmpp.NS_VERSION)
		iq.setID("Bs-i%d" % Info["outiq"].plus())
		if self.client:
			disp = self.client.getDisp(disp)
		Balancer.add(disp).queue(self.version_answer, disp, iq, {"chat": chat, "nick": nick, "jid": jid})

	#	@safe
	# when unable to check:
	#<iq xmlns="jabber:client" to="test@matrix.bz/test" from="mrdoctorwho@jabber.ru/Psi+" id="Bs-i1" type="error"><query xmlns="jabber:iq:version" /><error code="503" type="cancel"><service-unavailable xmlns="urn:ietf:params:xml:ns:xmpp-stanzas" /></error></iq>
	@safe_kwargs
	def version_answer(self, disp, stanza, chat, nick, jid, callback):
		vercheck_logger.debug("version_answer %s/%s (%s)", chat, nick, jid)
		os, version, name = None, None, None
		if xmpp.isResultNode(stanza):
			children = stanza.getQueryChildren() or []
			for node in children:
				if node.getName() == "os":
					os = node.getData()
				if node.getName() == "version":
					version = node.getData()
				if node.getName() == "name":
					name = node.getData()
				if os and version and name:
					break
		else:
			vercheck_logger.error("no result node! stanza: %s", stanza)
		config = self.Config[chat]
		_os = config["data"]["os"]
		_name = config["data"]["name"]
		for o in _os:
			if os == o["what"]:
				vercheck_logger.debug("match found os '%s' matches rule '%s'" % (name, o["what"]))
				_action = o["action"]
				self.version_action(nick, jid, chat, _action)
				break

		for n in _name:
			if name == n["what"]:
				vercheck_logger.debug("match found name '%s' matches rule '%s'" % (name, o["what"]))
				_action = n["action"]
				self.version_action(nick, jid, chat, _action)
				break

		onResult = self.onResult.get(jid)
		if onResult:
			onResult[0](**onResult[1])
			try:
				del self.onResult[jid]
			except KeyError:
				pass

	def version_action(self, nick, jid, chat, action=None):
		"""
		Called when need to fire an action
		"""
		vercheck_logger.debug("action %s for %s", action, jid)
		if jid in self.onResult:
			vercheck_logger.debug("jid %s is in onReult", jid)
			self.onResult[jid][1]["allow"] = False
		else:
			vercheck_logger.debug("jid %s is in onReult, action: %s", jid, action)
			Reason = "%s: Banned." % get_nick(chat)
			if action == "kick":
				Chats[chat].kick(nick, Reason)
			elif action == "ban":
				Chats[chat].outcast(jid, Reason)
			elif action == "visitor":
				Chats[chat].visitor(nick, Reason)
			elif action == "member":
				Chats[chat].member(jid, Reason)
			elif action == "moderator":
				Chats[chat].moder(nick, Reason)

	def find(self, chat, name=None, os=None):
		for val in self.Config[chat]["data"]["name"]:
			if val.get("what") == name:
				return val
		for val in self.Config[chat]["data"]["os"]:
			if val.get("what") == os:
				return val
		return False

	def vercheck_command(self, stype, source, body, disp):
		chat = source[1]
		lang = getLang(source)
		AnsBase = self.getAnswers(lang).base
		if body:
			if chat in Chats:
				if chat not in self.Config:
					self.Config[chat] = {"limit": 0, "data": {"name": [], "os": []}}  # {"limit": 0, data: [{"ver": ver, "action": action}]}
				args = body.split(" ", 1)
				lang = Chats.get(source[1]).get_user(source[2]).lang or DefLANG
				AnsBase = self.getAnswers(lang).base
				if len(args) > 1:
					action = args.pop(0)
					if action == "add":
						vars = args[0].split(" ", 2)
						if len(vars) > 2:
							type, chat_action, ver = vars
							found = False
							if type in ["name", "os"]:
								dict = {type: ver}
								if chat_action in self.actions:
									found = self.find(chat, **dict)
									if found:
										answer = AnsBase[12]
									else:
										self.Config[chat]["data"][type].append({"what": ver, "action": chat_action})
										answer = AnsBase[13] % (type, ver, chat_action)
								else:
									answer = AnsBase[0] % (chat_action, ", ".join(self.actions))
							else:
								answer = AnsBase[1] % type
						else:
							answer = AnsBase[2] % (len(vars))

					elif action == "del":
						vars = args[0].split(" ", 2)
						if len(vars) > 2:
							type, chat_action, ver = vars
							found = False
							if type in ["name", "os"]:
								found = False
								dict = {type: ver}
								if chat_action in self.actions:
									found = self.find(chat, **dict)
									if found:
										self.Config[chat]["data"][type].remove(found)
										answer = AnsBase[3] % (type, ver, chat_action)
									else:
										answer = AnsBase[4]
								else:
									answer = AnsBase[0] % (chat_action, ", ".join(self.actions))
							else:
								answer = AnsBase[1] % type
						else:
							answer = AnsBase[5] % (len(vars))

					elif action == "set":
						vars = args[0].split(" ")
						if len(vars) > 1:
							mode, number = vars
							if mode == "limit":
								if isNumber(number) and int(number) > 0:
									self.Config[chat]["limit"] = int(number)
									answer = AnsBase[14]
								else:
									answer = AnsBase[6]
							else:
								answer = AnsBase[7]
						else:
							answer = AnsBase[6]
					else:
						answer = AnsBase[8] % action
				else:
					args = body.split()
					answer = ""
					if len(args) == 1:
						if args[0] in ["show", "list"]:
							if self.Config[chat]["data"]["os"]:
								answer += AnsBase[9]
								for num, item in enumerate(self.Config[chat]["data"]["os"], 1):
									answer += "%s. %s → %s\n" % (num, item["what"], item["action"])
							if self.Config[chat]["data"]["name"]:
								answer += AnsBase[10]
								for num, item in enumerate(self.Config[chat]["data"]["name"], 1):
									answer += "%s. %s → %s\n" % (num, item["what"], item["action"])
							if not answer:
								answer = AnsBase[15]
						elif args[0] in ["1", "enable", "on"]:
							self.Config[chat]["enabled"] = True
							answer = AnsBase[14]
						elif args[0] in ["0", "disable", "off"]:
							self.Config[chat]["enabled"] = False
							answer = AnsBase[14]
					else:
						answer = AnsBase[5] % (len(args))
				cat_file(chat_file(chat, self.ConfFile), str(self.Config[chat]))
			else:
				return False
		else:
			answer = AnsBase[16]
			if chat in self.Config:
				if self.Config[chat]["enabled"]:
					answer += AnsBase[17]
				else:
					answer += AnsBase[18]
			else:
				answer += AnsBase[19]
		Answer(answer, stype, source, disp)

	def vercheck_04eh(self, chat, nick, source_, role, stanza, disp):
		if source_ and nick != get_nick(chat) and role[1] != "moderator":
			jid = stanza.getJid()# or source_
			try:
				jid, res = jid.split("/")
			except Exception:
				return False
			disp = Clients.get(disp, disp)
			if chat in self.Config and self.Config[chat]["enabled"]:
				self.version_check(chat, disp, nick, jid, res)

	def vercheck_01si(self, chat):
		config = deepcopy(self.defaults)
		filename = chat_file(chat, self.ConfFile)
		if initialize_file(filename, str(config)):
			config.update(eval(get_file(filename)))
		self.Config[chat] = config

	def vercheck_02si(self):
		if USE_SEPARATE_CLIENT:
			self.client = Child(USERNAME, SERVER, PASSWORD, NICKNAME)
			self.client.connect().auth().finish()

	commands = ((vercheck_command, "vercheck", 6,),)

	handlers = ((vercheck_01si, "01si"), (vercheck_02si, "02si"), (vercheck_04eh, "04eh"))
