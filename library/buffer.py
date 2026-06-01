# coding: utf-8

class buffer(object):
	""" list-style class used to make less code """
	def __init__(self):
		self.list = []

	split = lambda self, body: body.split(":", 1)[-1]

	def append(self, item):
		""" adds dict into the list """
#		if item not in self.list:
		self.list.append(item)

	def index(self, *args):
		try:
			result = self.list.index(*args)
		except ValueError:
			result = 0
		return result

	def remove_inst(self, item):
		""" removes the item instanly """
#		index = self.index(dict)
		#if index:
		if item in self.list:
			self.list.remove(item)

	def remove(self, key, val):
		""" removes self.list[..] -> dict
			where dict[key] == val
		"""
		result = self.filter(key, val)
		for key in result:
			if key in self.list:
				self.list.remove(key)

	def filter(self, key, val, special=False):
		""" return a list of dicts
			where list[..] -> dict
			&& dict[key] == val
		"""
		result = []
		for dict in self.list:
			if special is False:
				val_ = dict[key]
			else:
				val_ = dict[key][special]
			if val_ == val:
				result.append(dict)
		return result

	def len(self, key, val, special=False):
		""" return length of self.list
			where list[..] -> dict
			&& dict[key] == val
		"""
		return len(self.filter(key, val, special))

	def clear(self):
		self.list = []

	def reset(self, jid):
		""" just a shortcut for self.remove
			removes all jid references in self.list """
		self.remove("jid", jid)

	def __len__(self):
		""" return list length """
		return self.list.__len__()
