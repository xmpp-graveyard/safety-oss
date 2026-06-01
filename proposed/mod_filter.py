# coding: utf-8

#  BlackSmith mark.2
# exp_name = "muc-filter" # /code.py v.2.2e
#  Id: 2~1c
#  Code © 2014 — 2015 by mrDoctorWho

## System imports
import fcntl
import logging
import os
import random
import re
import socket
import struct
import sys
import threading
import urllib

from hashlib import sha1
from copy import deepcopy
from string import ascii_letters

## Local imports (this was used when the module was cythonized)
try:
	import xmpp
	import platform
	if os.path.exists("BlackSmith.py"):
		from __main__ import *
	else:
		from BlackSmith import *
	import paste
	import buffer as buff


except ImportError:
	import traceback
	traceback.print_exc()
	dynamic = "./%s"

LOG_LEVEL = logging.DEBUG
logFile = dynamic % "/filter.log"

logger = logging.getLogger("filter")
logger.setLevel(LOG_LEVEL)
loggerHandler = logging.FileHandler(logFile)
formatter = logging.Formatter("%(levelname)s %(asctime)s %(message)s", "[%d.%m.%Y %H:%M:%S]")
loggerHandler.setFormatter(formatter)
logger.addHandler(loggerHandler)

_std = sys.stdout
magic = ("*", "(", ")", ".", "+", "$", "^", "?", "*", "{", "}", "[","]", "|", "\\", "#")

isdef = lambda var: var in globals()


def escape(text):
	""" escapes a bunch of RE magic characters """
	text = list(text)
	for num, char in enumerate(text):
		if char in magic:
			text[num] = u"\\" + char
	return "".join(text)


def buildReply(stanza, typ, vars={}, tags={}):
	result = xmpp.Iq("result", to=stanza.getFrom())
	result.setID(stanza.getID()) # needed?
	query = xmpp.Node("query", {"xmlns": xmpp.NS_MUC_FILTER})
	node = xmpp.Node(typ, vars) # Does xml:lang needed?
	for tag in tags:
		node.setTagData(tag, tags[tag])
	query.addChild(node=node)
	result.addChild(node=query)
	Info["outiq"].plus()
	return result


def buildForbidReply(stanza, frm, chat, reason):
	iq = xmpp.Iq("result", to=chat)
	query = iq.setTag("query", namespace=xmpp.NS_MUC_FILTER)
	error = xmpp.ErrorNode(xmpp.ERR_FORBIDDEN, text=reason)
	presence = xmpp.Presence(frm, "error", frm=chat, payload=[error])
	query.addChild(node=presence)
	iq.setID(stanza.getID())
	stanza.setNamespace(xmpp.NS_CLIENT)
	Info["outiq"].plus()
	return iq


def getPresence(stanza):
	tag = stanza.getQuery(xmpp.NS_MUC_FILTER).getTag(xmpp.NS_PRESENCE)
	return xmpp.Presence(node=tag)


def getMessage(stanza):
	tag = stanza.getQuery(xmpp.NS_MUC_FILTER).getTag(xmpp.NS_MESSAGE)
	return xmpp.Message(node=tag)


class Queue:
	alive = True

	@classmethod
	def process(cls, buffer, filter=(), self=None, chat=None):
		"""
		processes the whole buffer
		sends messages from inside
		messages could be filtered
		"""
		if filter:
			list = buffer.filter(*filter)
			length = len(list)

		else:
			length = len(buffer)
			list = buffer.list

		for dict in list:
			diff = (time.time() - dict["time"])# + 1)
			if dict not in self.buffer[chat].list:
				logger.warning("dict not in self.buffer but in buffer!")
				continue

			if diff < QUEUE_TIMEOUT:
				time.sleep(diff)
				continue

			if diff > 10:
				buffer.remove_inst(dict)
				continue

			jid = dict["jid"]
			body = dict["body"]
			if self.check_please(chat, jid, body):
				if body[0] and not body[0].startswith(":"):
					body = ":".join(body)
				else:
					body = body[0] + body[1]
				stanza = dict["stanza"]
				disp = dict["disp"]
				message = getMessage(stanza)
				result = buildReply(stanza, "message", {"to": message.getTo(), "from": message.getFrom(), "type": message.getType(), "id": message.getID()}, {"body": body})
				try:
					list.remove(dict)
				except ValueError:
					pass
				Sender(disp, result)
				if length > 1:
					length -= 1
					time.sleep(0.13)  # 0.2

	@classmethod
	def cycle(cls, self, chat):
		""" buffer[chat] = [{stanza, jid, time, [..]}, {stanza, [..]}] """
		while cls.alive:
			buffer = self.buffer[chat]
			if buffer.list:
				cls.process(buffer, self=self, chat=chat)
			time.sleep(0.4)


def debug(msg, jid, chat):
	logger.debug("filtering out %s from %s because the %s", jid, chat, msg)


def getRandomString():
	i = 0
	string = ""
	length = random.choice([4, 5, 6])
	while i <= length:
		string += random.choice(ascii_letters)
		i += 1
	return string


class expansion_temp_(expansion):

	def __init__(self, name):
		defaults["badwords"] = deepcopy(Obscene)
		expansion.__init__(self, name)

	pattern = None
	FilterFile = "filt.db"
	JIDToNick = {}
	messages = {}
	join_times = {}
	obscenes = {}
	notified = {}
	hashes = {}
	buffer = {}
	antiflood = {}
	message_times = {}
	usernames = {}

	# filter values
	base = ("pvlock", "censor", "adv", "history", "fastjoin", "china", "pattern", "nickchange", "vercheck")
	numerical = {"lmsg": (0, 9000), "lnick": (0, 400), "lres": (0, 9000), "lstat": (0, 9000), "repeat": (0, 9000), "fastmsg": (0, 1000), "pastebin": (300, 4000), "same": (0, 300), "mention": (0, 100)}

	def command_filter(self, stype, source, body, disp):

		def change_cfg(chat, opt, state):
			if state in ("on", "1"):
				ChatsAttrs[chat]["filter"][opt] = True
				answer = AnsBase[4]
			elif state in ("off", "0"):
				ChatsAttrs[chat]["filter"][opt] = False
				answer = AnsBase[4]
			else:
				answer = AnsBase[2]
			return answer

		def alt_change_cfg(chat, opt, state, drange):
			if isNumber(state):
				state = int(state)
				if state in xrange(*drange) or state == 0:
					ChatsAttrs[chat]["filter"][opt] = state
					answer = AnsBase[4]
				else:
					answer = AnsBase[2]
			else:
				answer = AnsBase[30]
			return answer

		chat = source[1]
		answer = None
		if chat in Chats:
			filter = ChatsAttrs[chat]["filter"]
			if body:
				args = (body.lower()).split()
				arg0 = args.pop(0)
				if args:
					arg1 = args.pop(0)
					if enough_access(source[1], source[2], 6):
						if arg0 in self.base:
							answer = change_cfg(chat, arg0, arg1)

						elif arg0 in self.numerical:
							answer = alt_change_cfg(chat, arg0, arg1, self.numerical[arg0])

						elif arg0 == "caps_add":
							if arg1 not in filter["caps"]:
								filter["caps"].append(arg1)
								answer = AnsBase[4]
							else:
								answer = "This already exists."

						elif arg0 == "caps_del":
							if arg1 in filter["caps"]:
								filter["caps"].remove(arg1)
								answer = AnsBase[4]
							else:
								answer = "This doesn't exist."

						elif arg0 == "cens_add":
							arg1 = escape(arg1)
							if arg1 not in filter["badwords"]:
								filter["badwords"].append(arg1)
								self.obscenes[chat] = compile__(u"(?:%s)" % u"|".join(filter["badwords"]), 66)
								answer = AnsBase[4]
							else:
								answer = "This already exists."
						elif arg0 == "cens_del":
							arg1 = escape(arg1)
							if arg1 in filter["badwords"]:
								filter["badwords"].remove(arg1)
								self.obscenes[chat] = compile__(u"(?:%s)" % u"|".join(filter["badwords"]), 66)
								answer = AnsBase[4]
							else:
								answer = "This does not exist."
						elif arg0 == "cens_clear":
							filter["badwords"] = Obscene
							self.obscenes[chat] = compile__(u"(?:%s)" % u"|".join(Obscene), 66)
							answer = AnsBase[4]

					if not answer and arg0 == "pmlock":
						if arg1 in ("on", "1"):
							if source[2] not in filter["pvlocks"]:
								filter["pvlocks"].append(source[2])
								answer = AnsBase[4]
							else:
								answer = self.AnsBase["pv_filter"][0]
						elif arg1 in ("off", "0"):
							if source[2] in filter["pvlocks"]:
								filter["pvlocks"].remove(source[2])
								answer = AnsBase[4]
							else:
								answer = self.AnsBase["pv_filter"][1]
						else:
							answer = self.AnsBase["pv_filter"][2] if source[2] in filter["pvlocks"] else self.AnsBase["pv_filter"][3]

					elif not answer:
						answer = AnsBase[2]

				elif arg0 == "cens_list" and enough_access(source[1], source[2], 6):
					answer = ", ".join(filter["badwords"])
					Answer(AnsBase[11], stype, source, disp)
					stype = "chat"

				elif arg0 == "caps_list" and enough_access(source[1], source[2], 6):
					if filter["caps"]:
						answer = ""
						for num, itm in enumerate(filter["caps"], 1):
							answer += "\n%d. %s" % (num, itm)
					else:
						answer = "None."

				elif arg0 == "version":
					if isdef("VERSION"):
						answer = VERSION
					else:
						answer = "Warning! Running an unknown version from the source code."
				else:
					answer = AnsBase[1]
				if answer == AnsBase[4]:
					cat_file(chat_file(chat, self.FilterFile), str(filter))

			elif enough_access(source[1], source[2], 6):
				""" formatting configuration output """
				answer = "\n#-# MUC-Filter config:"
				for key in sorted(self.base):
					if key in filter:
						answer += self.AnsBase[key]
						if filter[key]:
							answer += self.AnsBase["ENABLED"]
						else:
							answer += self.AnsBase["DISABLED"]
				for key in self.numerical:
					answer += self.AnsBase[key] % (filter[key])
				answer += self.AnsBase["pmlock"]
				if source[2] in filter["pvlocks"]:
					answer += self.AnsBase["ENABLED"]
				else:
					answer += self.AnsBase["DISABLED"]

			elif source[2] in filter["pvlocks"]:
				answer = self.AnsBase["pv_filter"][4]
			else:
				answer = self.AnsBase["pv_filter"][5]
		else:
			answer = AnsBase[0]
		Answer(answer, stype, source, disp)

	compile_link = compile__("(?:http[s]?|ftp|svn)://[^\s'\"<>]+", 64)
	compile_chat = compile__("[^\s]+?@(?:conference|muc|conf|chat|group)\.[\w-]+?\.[\w-]+", 64)

	def tiser_checker(self, body):
		body = body.lower()
		if self.compile_link.search(body) or self.compile_chat.search(body):
			return True
		return False

	def obscene_checker(self, body, chat):
		if chat in self.obscenes and self.obscenes[chat]:
			exp = self.obscenes[chat]
			return exp.search(chr(32) + body + chr(32))
		return False

	def checkChina(self, nick):
		china = False
		for char in nick:
			try:
				num = ord(char)
				china = 35000 < num < 40000
				if china:
					break
			except Exception:
				continue
		return china

	# todo: remove stanza and add from and id
	def clearNotified(self):
		self.iters = 0
		while True:
			current = time.time()
			for user in self.notified.keys():
				if (current - self.notified[user]) > 40:
					del self.notified[user]
			for chat in self.join_times.keys():
				for user in self.join_times[chat].keys():
					if (current - self.join_times[chat][user][-1]) > 20:
						try:
							del self.join_times[chat][user]
						except KeyError:
							pass
			for jid in self.messages.keys():
				if (current - self.messages[jid]["times"][0]) > 100:
					try:
						del self.messages[jid]
					except KeyError:
						pass
			for chat in self.antiflood.keys():
				for jid in self.antiflood[chat].keys():
					if (current - self.antiflood[chat][jid]["time"]) > 7:
						try:
							del self.antiflood[chat][jid]
						except KeyError:
							pass
			for jid in self.message_times.keys():
				times = self.message_times[jid]
				if times:
					latest = times[-1]
					if (current - latest) > 150:
						try:
							del self.message_times[jid]
						except KeyError:
							pass
			time.sleep(10)


	def delete_crap(self, stanza):
		"""
		deletes some crap from the stanzas
		"""
		x = stanza.iterTags("x", {"xmlns": "vcard-temp:x:update"})
		try:
			stanza.kids.remove(x.next())
		except Exception:
			pass
		x = stanza.iterTags("stream")
		try:
			stanza.kids.remove(x.next())
			logger.debug("stream tag removed %s", stanza)
		except Exception:
			pass
		if stanza.getTag("c"):
			try:
				stanza.delChild("c")
			except Exception:
				pass
		try:
			stanza.delChild("priority")
		except Exception:
			pass
		return stanza

	# Todo: recover full body, currently it strips " " from the beginning
	def split(self, body):
		start, end = body.split(":", 1)
		if body.strip().startswith(":"):
			end = ":" + end
		return start, end

	def check_please(self, chat, jid, body):
		"""
		buffer contains messages list
		"""
		if jid not in self.antiflood.get(chat, {}):
			self.antiflood[chat][jid] = {"body": body, "times": 1, "time": time.time()}

		buffer = self.buffer[chat]

		""" the room's config """
		config = ChatsAttrs[chat]["filter"]

		""" message send flag. if true then message will be sent """
		send = True
		""" if user is known """
		""" antiflood contains base protection from sending similar messages """
		aflood = self.antiflood[chat][jid]

		""" check jid count in the room's buffer """
		jidCount = buffer.len("jid", jid)  # the hell is that? wtf the hell is that comment? # what the hell are ← those comments?

		# if user sends same messages
		""" if the last body is equal to previous """
		# todo: save some previous messages in here or in the buffer, buffer probably will be better
		# todo: maybe visitor for a while first time joined users?
		if config["same"] and aflood["times"] >= config["same"]:
			Chats[chat].outcast(jid, self.AnsBase["same_block"] % get_nick(chat))
			try:
				del self.antiflood[chat][jid]
			except KeyError:
				pass
			buffer.reset(jid)
			send = False

		if config["same"] and jidCount >= config["same"]:
			for dict in buffer.list:
				count = buffer.len("body", dict["body"], 1)
				if count >= config["same"]:
					send = False
					break

		if config["mention"] and jidCount >= config["mention"]:
			count = 0
			for nick in Chats[chat].get_nicks():
				count += buffer.len("body", nick.strip(), 0)
			if count >= config["mention"]:
				send = False
				if jid in self.JIDToNick[chat]:
					Chats[chat].kick(self.JIDToNick[chat][jid], self.AnsBase["mention_block"] % get_nick(chat))
		return send

	def flood_control(self, chat, jid, body, stanza, disp):
		"""
		remove nick or something from the body if any
		"""
		nick = ""
		if ":" in body:
			nick, body = self.split(body)
			nick = nick.strip()

		""" add some shits into the buffer. think about removing body and mb even disp """
		self.buffer[chat].append({"stanza": stanza, "time": time.time(), "jid": jid, "body": [nick, body], "disp": disp})

		""" if user isn't known """
		# what if ["body": body, "times": times]
		# should i make it in antiflood or its possible in buffer already?
		if jid not in self.antiflood[chat]:
			self.antiflood[chat][jid] = {"body": body, "times": 1, "time": time.time()}

		else:
			aflood = self.antiflood[chat][jid]
			self.check_please(chat, jid, body)
			if aflood["body"] == body:
				aflood["times"] += 1
			else:
				aflood["body"] = body
				aflood["times"] = 1

	# todo check what affects members and what doesn't
	# role could be checked in sUser class

	def notify(self, jid):
		""" 
		updates last notify time
		returns true if need to notify user
		"""
		if jid in self.notified:
			self.notified[jid] = time.time()
			return False
		self.notified[jid] = time.time()
		return True

	def decide(self, disp, stanza, to, frm, chat, tags, jid, allow=True):
		"""
		Decides whether to send the stanza depending on some contitions
		"""
		send = False
		if allow:
			result = buildReply(stanza, "presence", {"to": to, "from": frm}, tags)
			result = self.delete_crap(result)
			send = True
		else:
			if self.notify(jid):
				result = buildForbidReply(stanza, frm, chat, self.AnsBase["common_block"] % get_nick(chat))
				send = True
			if jid in self.usernames[chat].keys():
				del self.usernames[chat][jid]
		if send:
			Sender(disp, result)

	def filter_03eh(self, stanza, disp):
		if stanza.getQueryNS() == xmpp.NS_MUC_FILTER:
			chat = stanza.getFrom().getStripped()
			origQuery = stanza.getQuery(xmpp.NS_MUC_FILTER)
			presence = origQuery.getTag(xmpp.NS_PRESENCE)
			message = origQuery.getTag(xmpp.NS_MESSAGE)
			filter = ChatsAttrs[chat]["filter"]
			if presence:
				presence = xmpp.Presence(node=presence)
				""" to parts """
				to = presence.getTo()
				nick = to.getResource()
				""" from parts """
				frm = presence.getFrom()
				jid = frm.getStripped()
				res = frm.getResource() or ""
				""" presence shits """
				status = presence.getStatus() or ""
				show = presence.getShow() or ""
				caps = presence.getTagAttr("c", "node")
				""" user role """
				role = getattr(Chats[chat].get_user(nick), "role", ("none", "participant"))
				""" prevent moderators from sending presences. such a weird idea """
				if role[0] == "moderator":
					raise SelfExc()
				""" if user changes the nick """
				if presence.getStatusCode() == sCodes[1]:
					nick = presence.getNick()

				tags = {"status": status, "show": show}
				self.filter_04eh(chat, nick, None, None, None, None)
				if filter["history"]:
					history = True
					try:
						history = sum([int(val) for val in presence.getTag("x").getTag("history").getAttrs().values()])
						if history == 2:
							history = False
					except Exception:
						pass
					if not history:
						debug("presence history value is %d" % history, jid, chat)
						raise SelfExc()

				if len(nick) > filter["lnick"]:
					if self.notify(jid):
						reply = buildForbidReply(stanza, frm, chat, self.AnsBase["lnick_block"])
						Sender(disp, reply)
					debug("nick was too long (%d > %d)" % (len(nick), filter["lnick"]), jid, chat)
					raise SelfExc()

				elif len(res) > filter["lres"]:
					if self.notify(jid):
						reply = buildForbidReply(stanza, frm, chat, self.AnsBase["lres_block"])
						Sender(disp, reply)
					debug("resource was too long (%d > %d)" % (len(res), filter["lres"]), jid, chat)
					raise SelfExc()

				elif filter["censor"]:
					__nick = self.obscene_checker(nick, chat)
					__node = self.obscene_checker(frm.getNode(), chat)
					if __nick or __node:
						if self.notify(jid):
							reply = buildForbidReply(stanza, frm, chat, self.AnsBase["cens_block"])
							Sender(disp, reply)
						debug("presence cointains obscenes (nick: %s||%s, node: %s||%s)" % (nick, bool(__nick), frm.getNode(), bool(__node)), jid, chat)
						del __nick, __node
						raise SelfExc()

				if filter["fastjoin"] and role[1] in ("participant", "visitor"):
					Time = time.time()
					if chat not in self.join_times:
						self.join_times[chat] = {}

					if (Time - Chats[chat].sdate) >= 20:
						if jid not in self.join_times[chat]:
							self.join_times[chat][jid] = [time.time()]
						else:
							self.join_times[chat][jid].append(Time)
						if len(self.join_times[chat][jid]) > 3: # more #don't forget # i've forgotten, what?
							__diff = self.join_times[chat][jid][-1] - self.join_times[chat][jid].pop(0)
							if __diff < 10:#6
								Chats[chat].outcast(jid, self.AnsBase["fastjoin_block"] % get_nick(chat))
								debug("presences were sent too fast (%d > 10)" % __diff, jid, chat)
								raise SelfExc()

				if filter["china"]:
					__nick = self.checkChina(nick)
					__jid = self.checkChina(jid)
					if __nick or __jid:
						if self.notify(jid):
							reply = buildForbidReply(stanza, frm, chat, self.AnsBase["china_block"] % get_nick(chat))
							Sender(disp, reply)
						debug("presence cointained china chars (nick: %s, jid: %s)" % (__nick, __jid), jid, chat)
						raise SelfExc()

				if filter["caps"]:
					if caps in filter["caps"]:
						if self.notify(jid):
							reply = buildForbidReply(stanza, frm, chat, self.AnsBase["caps_block"] % get_nick(chat))
							Sender(disp, reply)
						debug("presence contains blocklisted caps (%s)" % caps, jid, chat)
						raise SelfExc()

				if self.pattern and filter["pattern"]:
					try:
						expansions["regexp"].pattern_04eh(chat, nick, frm, None, presence, disp)
					except SelfExc as e:
						if self.notify(jid):
							reply = buildForbidReply(stanza, frm, chat, self.AnsBase["pattern_block"] % get_nick(chat))
							Sender(disp, reply)
						debug("presence ran into pattern-based filter (`%s`)" % (e.message), jid, chat)
						raise SelfExc()

				if status:
					if len(status) > filter["lstat"]:
						tags = {}
						debug("presence is too long (%d > %d)" % (len(status), filter["lstat"]), jid, chat)
					elif filter["censor"] and self.obscene_checker(status, chat):
						tags = {}
						debug("presence cointain obscene (/*%s*/)" % status, jid, chat)
					elif filter["adv"] and self.tiser_checker(status):
						debug("presence cointain advertisements (/*%s*/)" % status, jid, chat)
						tags = {}

				# todo: ignore same presences from gmail?
				if filter["nickchange"]:
					"""
					Changes user's nickname to something like user_<random_stuff>
					"""
					if jid in self.usernames[chat]:
						raise SelfExc()
					else:
						nick = "user_%s" % getRandomString()
						self.usernames[chat][jid] = nick
					tags["status"] = random.choice(CRIME_MESSAGES)
					tags["show"] = "chat"
					to = "%s/%s" % (chat, nick)

				if filter.get("vercheck") and "vercheck" in expansions:
					logger.debug("triggering vercheck for %s in room %s", jid, chat)
					vercheck = expansions["vercheck"]
					vercheck.onResult[jid] = [self.decide, {"disp": disp, "stanza": stanza, "chat": chat, "to": to, "frm": frm, "jid": jid, "tags": tags}]
					vercheck.version_check(chat, disp, nick, jid, res)
					raise SelfExc()

				result = buildReply(stanza, "presence", {"to": to, "from": frm}, tags)
				Sender(disp, self.delete_crap(result))

			elif message:
				message = xmpp.Message(node=message)
				self.delete_crap(message)
				source = message.getFrom()
				jid = source.getStripped()
				to = message.getTo()
				mType = message.getType()
				body = message.getBody()
				real_body = body
				if not to:
					debug("warn: fetched message without a \"to\" attribute (ignoring): %s", str(message))
					raise SelfExc()
				tonick = to.getResource()
				nick = self.JIDToNick[chat].get(jid, "")

				if filter["lmsg"] and len(body) > filter["lmsg"]:
					debug("message is too long", jid, chat)
					raise SelfExc()

				elif filter["pastebin"] and len(body) > filter["pastebin"]:
					url = paste.makePaste(body, nick[:20], chat)
					body = body[:40] + u" [...]\n\nView paste (%d lines/%d chars): %s" % (body.count("\n"), len(body), url)
					debug("message was sent to the paste service", jid, chat)

				elif filter["censor"] and self.obscene_checker(body, chat):
					if self.notify(jid):
						Sender(disp, buildReply(stanza, "message", {"to": source, "from": to, "type": mType}, {"body": self.AnsBase["cens_block"]}))
					debug("user sends obscence", jid, chat)
					raise SelfExc()

				elif filter["adv"] and self.tiser_checker(body):
					debug("user sends advertisements", jid, chat)
					raise SelfExc()

				elif filter["pvlock"] and mType == "chat":
					if self.notify(jid):
						Sender(disp, buildReply(stanza, "message", {"to": source, "from": to, "type": mType}, {"body": self.AnsBase["pv_block"]}))
					debug("private locked at all", jid, chat)
					raise SelfExc()

				if tonick in filter["pvlocks"]:
					if self.notify(jid):
						Sender(disp, buildReply(stanza, "message", {"to": source, "from": to, "type": mType}, {"body": self.AnsBase["user_pv_block"]}))
					debug("%s's private locked" % tonick, jid, chat)
					raise SelfExc()

				if jid in self.messages:
					if self.messages[jid]["msg"] == real_body: ## real_body?
						self.messages[jid]["times"].append(time.time())
					else:
						self.messages[jid]["times"] = [time.time()]
					if len(self.messages[jid]["times"]) >= filter["repeat"]:
						diff = self.messages[jid]["times"][-1] - self.messages[jid]["times"][0] # pop?
						if diff < 10:
							Chats[chat].kick(self.JIDToNick[chat][jid], self.AnsBase["repeat_block"])
							try:
								del self.messages[jid]
							except KeyError:
								pass
							debug("user sends too fast", jid, chat)
							raise SelfExc()
				else:
					self.messages[jid] = {"times": [time.time()], "msg": real_body}
				self.messages[jid]["msg"] = real_body

				# rewrite to self.messages?		
				if filter["fastmsg"]:
					if jid in self.message_times:
						self.message_times[jid].append(time.time())
						if len(self.message_times[jid]) > 2:
							diff = self.message_times[jid].pop() - self.message_times[jid].pop(0) # -1 / 0
							if diff < filter["fastmsg"]:
								Chats[chat].kick(self.JIDToNick[chat][jid], self.AnsBase["fastmsg_block"] % get_nick(chat))
								try:
									del self.message_times[jid]
								except KeyError:
									pass
								logger.debug("sends too fast", str(jid))
								raise SelfExc()
					else:
						self.message_times[jid] = []

				if filter["china"]:
					if self.checkChina(body):
						if self.notify(jid):
							Sender(disp, buildReply(stanza, "message", {"to": source, "from": to, "type": mType}, {"body": self.AnsBase["china_block"]}))
						debug("user sends china message", jid, chat)
						raise SelfExc()

				if filter["same"] or filter["mention"]:
					self.flood_control(chat, jid, body, stanza, disp)  # todo: add flags to send/deny sending message

				else:
					result = buildReply(stanza, "message", {"to": to, "from": source, "type": mType}, {"body": body})
					Sender(disp, result)


	def filter_01si(self, chat):
		# sometimes we don't have any attrs for some reason
		if chat not in ChatsAttrs:
			ChatsAttrs[chat] = {}
		desc = ChatsAttrs[chat]
		desc["filter"] = deepcopy(defaults)
		filename = chat_file(chat, self.FilterFile)
		if expansions.get("regexp"):
			self.pattern = True
		if self.pattern:
			expansions["regexp"].actions.add("filter")
		if initialize_file(filename, str(desc["filter"])):
			dict = eval(get_file(filename))
			desc["filter"].update(dict)
		self.buffer[chat] = buff.buffer()
		self.antiflood[chat] = {}
		self.usernames[chat] = {}
		self.obscenes[chat] = compile__(u"(?:%s)" % u"|".join(desc["filter"]["badwords"]), 66)
		sThread("Queue.cycle-%s" % chat, Queue.cycle, (self, chat))

	def filter_02si(self):
		composeThr(self.clearNotified, "clearNotified").start()

	def filter_04eh(self, chat, nick, source_, role, stanza, disp):
		if chat not in self.JIDToNick:
			self.JIDToNick[chat] = {}
		if not role or role[1] != "moderator":
			self.JIDToNick[chat][source_] = nick

	# unavailable presences
	def filter_05eh(self, chat, nick, status, scode, disp):
		jid = get_source(chat, nick)
		if chat in self.JIDToNick and jid in self.JIDToNick[chat]:
			del self.JIDToNick[chat][jid]
		if chat in self.usernames and jid in self.usernames[chat]:
			del self.usernames[chat][jid]

	commands = ((command_filter, "filter", 1),)

	handlers = (
		(filter_01si, "01si"),
		(filter_02si, "02si"),
#		(filter_04si, "04si"),
		(filter_03eh, "03eh"),
		(filter_04eh, "04eh"),
		(filter_05eh, "05eh")
	)

expansion_temp = expansion_temp_
