# coding: utf-8

class expansion_temp(expansion):

	def __init__(self, name):
		expansion.__init__(self, name)

	def getAnswers(self, lang):
		if lang in self.langs:
			return self.langs[lang]
		if DefLANG in self.langs:
			return self.langs[DefLANG]
		return self.langs.values()[0]

	def command_caps(self, stype, source, nick, disp):
		chat = source[1]
		AnsBase = self.getAnswers(DefLANG.lower()).base
		answer = AnsBase[0]
		if source[1] in Chats:
			chat = Chats.get(source[1])
			lang = chat.get_user(source[2]).lang or DefLANG
			AnsBase = self.getAnswers(lang).base
			if nick:
				user = chat.get_user(nick)
				answer = ""
				if user:
					caps = user.caps
					for key in caps.keys():
						answer += "%s: %s | " % (key, caps[key])
				else:
					answer = AnsBase[1]
			else:
				answer = AnsBase[1]

		Answer(answer, stype, source, disp)

	commands = (
		(command_caps, "caps", 1,),
	)
