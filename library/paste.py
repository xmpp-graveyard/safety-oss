# coding: utf-8

from BlackSmith import Web, collectExc


def makePaste(body, poster, room):
	answer = "Something went wrong"
	if body:
		title = "%s — %s" % (poster, room)
		Opener = Web("http://matrix.bz/en/paste/index-without-csrf",
			data=Web.encode({"Paste[body]": body.encode("utf-8"),
				"Paste[text]": "",
				"Paste[expiration]": "2",
				"Paste[language]": "0",
				"Paste[access]": "90",
				"Paste[title]": title}))
		try:
			fp = Opener.open(("Mozilla/5.0", "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:21.0) Gecko/20130309 Firefox/21.0"))
			url = fp.url
			id = url.split("/")[-1]
			answer = "http://matrix.bz/paste/download?id=%s" % id
			fp.close()
		except Web.Two.HTTPError as exc:
			answer = str(exc)
		except Exception:
			collectExc(makePaste)
	return answer