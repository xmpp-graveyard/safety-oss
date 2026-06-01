# coding: utf-8

import xmpp


class expansion_temp(expansion):

	domain_whitelist = ["example.com", "helloworld.net"]

	def __init__(self, name):
		expansion.__init__(self, name)


	def server_whitelist_04eh(self, chat, nick, jid, role, stanza, disp):
		if chat in Chats:
			sChat = Chats[chat]
			if not jid or "@" not in jid:
				return
			jid_obj = xmpp.JID(jid)
			if role[1] == "visitor":
				if jid_obj and jid_obj.getDomain() in self.domain_whitelist:
					sChat.participant(nick, reason="face control")

	handlers = (
		(server_whitelist_04eh, "04eh"),
	)
