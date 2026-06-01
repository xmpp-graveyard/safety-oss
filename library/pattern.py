"""
BlackSmith bot's module "pattern"
pattern.py

Copyright (2013) Al Korgun (alkorgun@gmail.com)

Distributed under the GNU GPLv3.
"""

__all__ = [
	"Pattern",
	"JIDPattern",
	"NickPattern"
				]

__version__ = "0.3"

class Pattern(object):

	any_chars = "*"
	escape_any_chars = "\\*"
	sub = "#"

	def __init__(self, pattern):
		self.pattern = pattern

	def get_part(self, part):
		part, escape_map = self.escape(part)
		any_start = part.startswith(self.any_chars)
		any_end = part.endswith(self.any_chars)
		part = self.unescape(part.strip(self.any_chars), escape_map, len(part) - len(part.lstrip(self.any_chars)))
		return (any_start, part, any_end)

	def escape(self, part):
		escape_map = []
		offset = len(self.escape_any_chars)
		for x in xrange(part.count(self.escape_any_chars)):
			x = part.find(self.escape_any_chars)
			part = part[:x] + self.sub + part[x + offset:]
			escape_map.append(x)
		return part, escape_map

	def unescape(self, part, escape_map, offset = 0):
		part = list(part)
		for x in escape_map:
			part[x - offset] = self.any_chars
		return "".join(part)

	def eq(self, pattern, any_start, part, any_end):
		if not part:
			return True
		if any_start:
			if any_end:
				if part not in pattern:
					return False
			elif not pattern.endswith(part):
				return False
		elif any_end:
			if not pattern.startswith(part):
				return False
		elif part != pattern:
			return False
		return True

	def normalize_part(self, part):
		if part[1]:
			part = list(part)
			part[0] = self.any_chars if part[0] else ""
			part[1] = part[1].replace(self.any_chars, self.escape_any_chars)
			part[2] = self.any_chars if part[2] else ""
			part = "".join(part)
		else:
			part = self.any_chars
		return part

	__str__ = __repr__ = lambda self: "%s(%s)" % (self.__class__.__name__, str(self.pattern))

class JIDPattern(Pattern):

	import re

	comp = re.compile("(.+)@(.+)/(.+)")

	def __init__(self, pattern):
		if isinstance(pattern, tuple):
			self.pattern = pattern
		else:
			temp = []
			for part in self.split(pattern):
				temp.append(self.get_part(part))
			self.pattern = tuple(temp)

	@classmethod
	def split(cls, jid):
		jid = cls.comp.search(jid)
		assert jid, "this can't be a JID!"
		return jid.groups()

# 	def __eq__(self, pattern):
# 		for (any_start, ppart, any_end), jpart in zip(self.pattern, pattern):
# 			if not self.eq(jpart, any_start, ppart, any_end):
# 				return False
# 		return True

	def __eq__(self, pattern):
		for (any_start, ppart, any_end), jpart in zip(self.pattern, pattern):
			if not ppart:
				continue
			if any_start:
				if any_end:
					if ppart not in jpart:
						return False
				elif not jpart.endswith(ppart):
					return False
			elif any_end:
				if not jpart.startswith(ppart):
					return False
			elif ppart != jpart:
				return False
		return True

	def normalize(self):
		pattern = [self.normalize_part(part) for part in self.pattern]
		pattern.insert(1, "@")
		pattern.insert(3, "/")
		return "".join(pattern)

class NickPattern(Pattern):

	def __init__(self, pattern):
		if isinstance(pattern, tuple):
			self.pattern = pattern
		else:
			self.pattern = self.get_part(pattern)

	def __eq__(self, pattern):
		return self.eq(pattern, *self.pattern)

	def normalize(self):
		return self.normalize_part(self.pattern)


def main():
	pass