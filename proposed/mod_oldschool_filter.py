# coding: utf-8

#  BlackSmith mark.2
# exp_name = "muc-filter" # /code.py v.2.2e
#  Id: 2~1c
#  Code © 2014 — 2015 by mrDoctorWho

## System imports
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

## Local imports
try:
	import xmpp
	import platform
	if os.path.exists("BlackSmith.py"):
		from __main__ import *
	else:
		from BlackSmith import *


except ImportError:
	import traceback
	traceback.print_exc()
	dynamic = "./%s"
import utils

LOG_LEVEL = logging.DEBUG
logFile = dynamic % "/oldschool_filter.log"

logger = logging.getLogger("oldschool_filter")
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


class ChatUser(object):
	def __init__(self, chat, jid, nick):
		self.join_time = time.time()
		self.last_message_time = 0
		self.chat = chat
		self.jid = jid
		self.nick = nick

	def setNick(self, newNick):
		self.nick = newNick
		return self

	def setJid(self, newJid):
		self.jid = newJid
		return self

	def updateLastMessageTime(self):
		self.last_message_time = time.time()


SENTENCE_DUE = 100 # seconds
PROBATION_PERIOD = 60 # seconds


import datetime
timefmt = lambda ts: datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

class Prison(object):
	def __init__(self, chat):
		# suspect objects
		self.prisoners = []
		self.chat = chat
		self.running = False

	def start(self):
		# todo it's better to have a thread outside to rule all prisons
		# but it'll be done like this b/c we only have a few chats now
		if not self.running:
			#utils.runThread(self.cleanup, name="prison@%s" % self.chat)
			self.running = True

	def put(self, prisoner):
		if prisoner not in self.prisoners:
			sentence = prisoner.getSentence()
			self.prisoners.append(prisoner)
			sentence.takeAction()
			logger.debug("putting %s to prison; dude is set to be released at %s (now %s)", prisoner, timefmt(sentence.expires), timefmt(time.time()))

	def remove(self, prisoner):
		if prisoner in self.prisoners:
			self.prisoners.remove(prisoner)


	def cleanup(self):
		while self.running:
			for prisoner in self.prisoners:
				if (time.time() - prisoner.getSentence().expires >= 0):
					logger.debug("removing prisoner %s since his period has ended", prisoner)
					prisoner.free()
					prisoner.getSentence().setExpired()
					self.remove(prisoner)
			time.sleep(1)

	def has(self, jid):
		return jid in self.prisoners


class Suspect(object):
	def __init__(self, chat, jid):
		self.chat = chat
		self.jid = jid
		self.emprisoned = time.time()
		self.violations = 0
		self.sentence = None

	def jail(self, sentence):
		self.sentence = sentence
		return self

	def free(self):
		self.sentence.getCourtAction().release()

	def getSentence(self):
		return self.sentence

	def setSentence(self, sentence):
		self.sentence = sentence
		return self

	def isDue(self):
		return time.time() - self.getSentence().expires >= 0

	def __str__(self):
		return "%s from %s" % (self.jid, self.chat)

	def __eq__(self, other):
		if isinstance(other, Suspect):
			other_jid = other.jid
		else:
			other_jid = other
		return other_jid == self.jid


class Probation(object):
	def __init__(self):
		self.due = time.time() + PROBATION_PERIOD

	def isExpired(self):
		return time.time() - prisoner.due >= 0


class Sentence(object):

	def __init__(self, expires=None, court_action=None):
		# self.sentence = sentence
		self.expired = False
		self.on_probation = False
		self.court_action = court_action
		if not expires:
			expires = time.time() + SENTENCE_DUE
		self.expires = expires

	def setExpired(self, need_probation=True):
		self.expired = True
		self.on_probation = need_probation

	def setProbationEnd(self):
		self.on_probation = False

	def takeAction(self):
		self.court_action.takeAction()

	def getCourtAction(self):
		return self.court_action


class CourtAction(object):

	def __init__(self, chat, jid, nick, action="visitor"):
		# self.law_article
		self.chat = chat
		self.jid = jid
		self.nick = nick
		self.action = action


	def takeAction(self):
		Reason = "%s: taking action." % get_nick(self.chat)
		action = self.action
		if action == "kick":
			Chats[chat].kick(self.nick, Reason)
		elif action == "ban":
			Chats[self.chat].outcast(self.jid, Reason)
		elif action == "visitor":
			Chats[self.chat].visitor(self.nick, Reason)
		elif action == "member":
			Chats[self.chat].member(self.jid, Reason)
		elif action == "moderator":
			Chats[self.chat].moder(self.nick, Reason)
		logger.debug("Took action: %s on %s in %s", self.action, self.jid, self.chat)


	def release(self):
		Chats[self.chat].none(self.jid, "Released from jail. You're now on probation.")
		logger.debug("Released: %s from jail in %s", self.jid, self.chat)



class LawArticle(object):
	# timeout, probation period, action after timeout, action if violated in a probation period

	# todo: name/type/action/number-of-violations
	law =  {"MESSAGES_PER_SECOND_LIMIT": (10, 600, "visitor", "kick"),
	"MENTION_LMIT": (60, 600, "visitor", "kick"),
	"MESSAGE_SIZE": 1000}

	def checkViolation(self):
		pass


class MessageObject(object):

	def __init__(self, size=0, mentions=0):
		self.date = time.time()
		self.size = size
		self.mentions = 0


class Keeper(object):
	def __init__(self):
		self.prisons = {}
		self.suspects = {}


keeper = Keeper()


class OldSchoolFilter(expansion):

	def __init__(self, name):
		expansion.__init__(self, name)

	keeper.prisons = {}
	keeper.suspects = {}

	# message
	def filter_01eh(self, stanza, isConf, stype, source, body, isToBs, disp):
		source, chat, nick = source
		if chat in Chats:
			sChat = Chats[chat]
			sUser = sChat.get_user(nick)
			prisons = keeper.prisons
			prison = prisons.get(chat)
			if not prison:
				prison = Prison(chat)
				prison.start()
			suspects = keeper.suspects.get(chat)
			if not suspects:
				suspects = suspects[chat] = {}
			jid = sUser.source
			suspect = suspects.get(jid)
			if not suspect:
				suspect = suspects[jid] = Suspect(chat, jid)

			role = getattr(sChat.get_user(nick), "role", ("none", "participant"))
			if role[0] != "none":
				return

			if prison.has(jid):
				logger.warning("this shouldn't have happened, but an emprisoned persion managed to send a message")

			# message length violation
			if len(body) > 100:
				action = CourtAction(chat, jid, nick)
				sentence = Sentence(court_action=action)
				suspect.setSentence(sentence)
				prison.put(suspect)
				del suspects[jid]

	@staticmethod
	def get_prison(chat, start=True):
		if chat in Chats:
			prisons = keeper.prisons
			prison = prisons.get(chat)
			if not prison:
				prison = prisons[chat] = Prison(chat)
				if start:
					prison.start()
			return prison
		return None


	@staticmethod
	def get_suspect(chat, jid):
		if chat in Chats:
			suspects = keeper.suspects.get(chat)
			if not suspects:
				suspects = keeper.suspects[chat] = {}
			suspect = suspects.get(jid)
			if not suspect:
				suspect = suspects[jid] = Suspect(chat, jid)
			return suspect
		return None


	def filter_04eh(self, chat, nick, jid, role, stanza, disp):
		if chat in Chats:
			sChat = Chats[chat]
			prison = OldSchoolFilter.get_prison(chat)
			if prison.has(jid):
				suspect = OldSchoolFilter.get_suspect(chat, jid)
				if not suspect.isDue():
					suspect.getSentence().takeAction()




	def filter_01si(self, chat):
		# sometimes we don't have any attrs for some reason
		if chat not in ChatsAttrs:
			ChatsAttrs[chat] = {}
		chatObj = Chats.get(chat)
		if chatObj:
		# starting point for every chat the bot joins

	def filter_02si(self):
		# starting point for everything
		pass


	# unavailable presences
	def filter_05eh(self, chat, nick, status, scode, disp):
		jid = get_source(chat, nick)


	# commands = ((command_filter, "filter", 1),)

	handlers = (
		(filter_01si, "01si"),
		(filter_02si, "02si"),
		(filter_01eh, "01eh"),
#		(filter_04si, "04si"),
		# (filter_03eh, "03eh"),
		(filter_04eh, "04eh"),
		(filter_05eh, "05eh")
	)


#%%%%%


expansion_temp = OldSchoolFilter
