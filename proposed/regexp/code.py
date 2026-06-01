# coding: utf8
from pattern import *

def check_jid_for_matches(jid, Patterns = None):
	if not Patterns:
		return False
	jid = JIDPattern.split(jid)
	for pattern in Patterns:
		if pattern == jid:
			return pattern
	return False

def check_nick_for_matches(nick, Patterns = None):
	if not Patterns:
		return False
	for pattern in Patterns:
		if pattern == nick:
			return pattern
	return False

class expansion_temp(expansion):

	def __init__(self, name):
		expansion.__init__(self, name)

	actions = set(["visitor", "kick", "ban", "member", "moderator"])

	def pattern_action(self, chat, nick, jid, matched, key):
		action = self.Patterns[chat][key][matched]
		Reason = "%s: Banned." % get_nick(chat)
		#"%s: Sorry, but your %s matches pattern: %s" % (get_nick(chat), key, matched.normalize())
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
		elif action == "filter":
			raise SelfExc(matched.normalize())

	def pattern_04eh(self, chat, nick, source_, role, stanza, disp):
		if source_ and nick != get_nick(chat):
			jid = stanza.getJid() or source_
			jid = str(jid)
			matched_nick = check_nick_for_matches(nick, self.Patterns[chat]["nick"].keys())
			if matched_nick:
				self.pattern_action(chat, nick, jid, matched_nick, "nick")
			else:
				matched_jid = check_jid_for_matches(jid, self.Patterns[chat]["jid"].keys())
				if matched_jid:
					self.pattern_action(chat, nick, jid, matched_jid, "jid")

	def pattern_command(self, stype, source, body, disp):
		room = source[1]
		if body:
			body = body.split() # 0: add/del; 1: jid/nick; 2: *@jabber.ru; 3: kick/ban/member (lol)
			if len(body) > 2:
				What = body.pop(1)
				foo = {"jid": (JIDPattern, check_jid_for_matches),
						"nick": (NickPattern, check_nick_for_matches)}
				if What in foo:
					Type = (body.pop(0)).lower()
					Pattern_raw = body.pop(0)
					if Type == "add":
						if body:
							Action = (body.pop(0)).lower()
							if Action in self.actions:
								try:
									Pattern = foo[What][0](Pattern_raw)
								except AssertionError as text:
									answer = str(text)
								else:
									isPatternExists = foo[What][1](Pattern_raw, self.Patterns[room][What].keys())
									if not isPatternExists:
										self.Patterns[room][What][Pattern] = Action
										cat_file(chat_file(room, self.RegFile), str(self.Patterns[room]))
										answer = "Added: %(What)s match «%(Pattern_raw)s» → %(Action)s." % vars()
									else:
										answer = "Pattern «%s» already exists." % Pattern_raw
							else:
								answer = "Unknown action: %s." % Action
						else:
							answer = "no body, no game"
					elif Type == "del":
						try:
							Pattern = foo[What][1](Pattern_raw, self.Patterns[room][What].keys())
						except AssertionError as text:
							answer = str(text)
						else:
							if Pattern:
								del self.Patterns[room][What][Pattern]
								cat_file(chat_file(room, self.RegFile), str(self.Patterns[room]))
								answer = "ok"
							else:
								answer = "fail"
					else:
						answer = "undefined type"
				else:
					answer = "unknown parameter"
			elif len(body) == 1:
				Type = (body.pop(0)).lower()
				if Type == "clear":
					self.Patterns[room] = {"nick": {}, "jid": {}}
					cat_file(chat_file(room, self.RegFile), str(self.Patterns[room]))
					answer = "By the way, all patterns are gone!"
			else:
				answer = "need more body"

		else:
			if self.Patterns[room]:
				List = {"jid": [], "nick": []}
				nickPatterns = self.Patterns[room]["nick"]
				jidPatterns = self.Patterns[room]["jid"]
				for jPattern in sorted(jidPatterns.keys()):
					normal = jPattern.normalize()
					List["jid"].append("%s → %s" % (normal, jidPatterns[jPattern]))
				for nPattern in sorted(nickPatterns.keys()):
					normal = nPattern.normalize()
					List["nick"].append("%s → %s" % (normal, nickPatterns[nPattern]))
				answer = ""
				if List["jid"]:
					answer += "\n• JIDPatterns:\n"
					answer += enumerated_list(List["jid"])
				if List["nick"]:
					answer += "\n\n• NickPatterns:\n"
					answer += enumerated_list(List["nick"])
		if not answer:
			answer = "List is Empty."

		Answer(answer, stype, source, disp)


	Patterns = {}
	RegFile = "regexp.base"
	def pattern_01si(self, conf):
		patterns = {"nick": {}, "jid": {}}
		Name = chat_file(conf, self.RegFile)
		if initialize_file(Name, str(patterns)):
			patterns = eval(get_file(Name))
		self.Patterns[conf] = patterns
	commands = ((pattern_command, "pattern", 6,),)

	handlers = ((pattern_01si, "01si"), (pattern_04eh, "04eh"))