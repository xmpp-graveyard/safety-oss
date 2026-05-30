"""
Module "fb2"
fb2.py

Copyright (2011-2013) Al Korgun (alkorgun@gmail.com)

Distributed under the GNU GPLv3.
"""

from re import compile as compile__
from time import asctime

import htmlentitydefs

__all__ = [
	"htmlentitydefs",
	"edefs",
	"compile__",
	"asctime",
	"get_enc",
	"sub_all",
	"sub_titles",
	"get_text",
	"sub_desc",
	"get_data",
	"make"
]

__version__ = "0.1.8"

edefs = dict()

for Name, Numb in htmlentitydefs.name2codepoint.iteritems():
	edefs[Name] = unichr(Numb)

del Name, Numb

edefs["&apos;"] = unichr(39)

compile_st = compile__("<[^<>]+?>")
compile_ehtmls = compile__("&(#?[xX]?(?:[0-9a-fA-F]+|\w{1,8}));")
compile_stitle = compile__("<title>((?:.|\s)+?)</title>", 16)
compile_subtitle = compile__("<subtitle>((?:.|\s)+?)</subtitle>", 16)

def sub_titles(data):
	if data.count("<title>"):
		st = lambda co: "\n\n(*t)\t%s\n\n" % sub_desc(compile_st.sub("", co.group(1)).strip(), {chr(10): " - "})
		data = compile_stitle.sub(st, data)
	if data.count("<subtitle>"):
		st = lambda co: "\n\n(*sbt)\t%s\n\n" % sub_desc(compile_st.sub("", co.group(1)).strip(), {chr(10): " - "})
		data = compile_subtitle.sub(st, data)
	return data

def sub_ehtmls(data):
	if data.count("&"):

		def e_sb(co):
			co = co.group(1)
			if co.startswith("#"):
				if chr(120) == co[1].lower():
					Char, c06 = co[2:], 16
				else:
					Char, c06 = co[1:], 10
				try:
					Numb = int(Char, c06)
					assert (-1 < Numb < 65535)
					Char = unichr(Numb)
				except Exception:
					Char = edefs.get(Char, "&%s;" % co)
			else:
				Char = edefs.get(co, "&%s;" % co)
			return Char

		data = compile_ehtmls.sub(e_sb, data)
	return data

sub_all = lambda data: sub_ehtmls(compile_st.sub("", data)).strip()

def get_text(data, s0, s2, s1 = "(?:.|\s)+"):
	comp = compile__("%s(%s?)%s" % (s0, s1, s2), 16)
	data = comp.search(data)
	if data:
		data = (data.group(1)).strip()
	return data

get_enc = lambda data: get_text(data, "encoding=\"", "\"\?")

def sub_desc(data, ls, sub = str()):
	if isinstance(ls, dict):
		for x, z in ls.items():
			data = data.replace(x, z)
	else:
		for x in ls:
			if isinstance(x, (list, tuple)):
				if len(x) > 1:
					data = data.replace(*x[:2])
				else:
					data = data.replace(x[0], sub)
			else:
				data = data.replace(x, sub)
	return data

def get_data(data):
	data = sub_desc(data, [chr(10), chr(13), ("<p>", chr(10)), ("<v>", chr(10))]).strip()
	comp = compile__("<p.*?>")
	data = comp.sub(chr(10), data)
	desc = get_text(data, "<description>", "</description>")
	if desc:
		creator = get_text(desc, "<author>", "</author>")
		if creator:
			tl = ("first-name", "middle-name", "last-name")
			ls = []
			for tn in tl:
				td = get_text(creator, "<%s>" % tn, "</%s>" % tn)
				if td:
					ls.append(td)
			author = sub_all(str.join(chr(32), ls))
		else:
			author = None
		comp = compile__("<binary.+?content-type=\"image/(.+?)\".*?>((?:.|\s)+?)</binary>", 16)
		coverD = comp.search(data)
		if coverD:
			coverD = coverD.groups()
		genre = get_text(desc, "<genre>", "</genre>")
		annt = get_text(desc, "<annotation>", "</annotation>")
		name = get_text(desc, "<book-title>", "</book-title>")
		date = get_text(desc, "<date>", "</date>")
		if date:
			ls = date.split(".")
			try:
				date = int(ls[-1])
			except ValueError:
				date = None
		sequence = get_text(desc, "<sequence", "/>")
		if sequence:
			seq1, seq2 = get_text(sequence, "name=\"", "\""), get_text(sequence, "number=\"", "\"")
			if seq2:
				ls = seq2.split(".")
				try:
					seq2 = int(ls[-1])
				except ValueError:
					seq2 = None
		else:
			seq1, seq2 = None, None
		if seq1:
			seq1 = sub_all(seq1)
		if name:
			name = sub_all(name)
		if annt:
			annt = sub_all(annt)
		if genre:
			genre = sub_all(genre)
		desc = (name, author, date, genre, seq1, seq2, coverD, annt)
	body = get_text(data, "<body.*?>", "</body>")
	if body:
		comp = compile__("<section.*?>((?:.|\s)+?)</section>", 16)
		ls, sections = [], comp.findall(body)
		if sections:
			for body in sections:
				ls.append(sub_titles(body.strip()))
			body = sub_all(str.join(chr(10), ls))
	return (desc, body)

def make(body, Name, author = None, year = None, genre = None, seq1 = None, seq2 = 0, cover = None, annt = None, lang = "en", bs = "fb2.py %s" % (__version__), User = None):
	data = ['''<?xml version="1.0" encoding="UTF-8"?>
<FictionBook xmlns:l="http://www.w3.org/1999/xlink" xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">
<description>''']
	data.append("<title-info>")
	if genre:
		data.append("<genre>%s</genre>" % (genre))
	if author:
		data.append("<author>")
		ls = author.split()
		if len(ls) == 1:
			data.append("<last-name>%s</last-name>" % (ls.pop(0)))
		elif len(ls) == 2:
			data.append("<first-name>%s</first-name><last-name>%s</last-name>" % tuple(ls))
		else:
			first, last = ls.pop(0), ls.pop()
			data.append("<first-name>%s</first-name><middle-name>%s</middle-name><last-name>%s</last-name>" % (first, str.join(chr(32), ls), last))
		data.append("</author>")
	data.append("<book-title>%s</book-title>" % (Name))
	if annt:
		data.append("<annotation>")
		for line in annt.splitlines():
			data.append("<p>%s</p>" % (line.strip()))
		data.append("</annotation>")
	if year:
		data.append("<date>%s</date>" % str(year))
	if cover:
		data.append("<coverpage>\n<image l:href=\"#cover.%s\"/>\n</coverpage>" % cover[0])
	data.append("<lang>%s</lang>" % (lang.lower()))
	if seq1:
		if seq2:
			data.append("<sequence name=\"%s\" number=\"%s\"/>" % (seq1, seq2))
		else:
			data.append("<sequence name=\"%s\"/>" % (seq1))
	data.append("</title-info>")
	data.append("<document-info>")
	if User:
		data.append("<author>\n<nickname>%s</nickname>\n</author>" % User)
	data.append("<program-used>%s</program-used>" % bs)
	data.append("<date>%s</date>" % asctime())
	data.append("<version>2.0</version>")
	data.append("</document-info>")
	data.append("</description>")
	data.append("<body>")
	for line in body.splitlines():
		line = line.strip()
		if line:
			if line.startswith("(*t)"):
				if data[-1] != "<body>":
					data.append("</section>")
				data.append("<section>\n<title>\n<p>%s</p>\n</title>\n<empty-line />" % (line[4:].strip()))
			elif line.startswith("(*sbt)"):
				data.append("<subtitle>%s</subtitle>" % (line[6:].strip()))
			else:
				data.append("<p>%s</p>" % (line))
	data.append("</section>")
	data.append("</body>")
	if cover:
		data.append("<binary content-type=\"image/{0}\" id=\"cover.{0}\">{1}</binary>".format(*cover))
	data.append("</FictionBook>")
	return sub_desc(str.join(chr(10), data), ("(*t)", "(*sbt)"))
