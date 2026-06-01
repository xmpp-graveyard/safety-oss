# coding: utf-8
# © simpleApps, 2010

"""
Sometimes your program can crash with an error "IOError: device not ready" when it prints some text
This module is used to prevent such things
"""

import sys
import time

color0 = chr(27) + "[0m" # none
color1 = chr(27) + "[33m" # yellow
color2 = chr(27) + "[31;1m" # red
color3 = chr(27) + "[32m" # green
color4 = chr(27) + "[34;1m" # blue

def use_lsd(text):
	import random
	line = ""
	for char in text:
		style = random.choice((0, 1, 4, 5))
		background = random.randrange(41, 48)
		style = "%s;30;%s" % (style, background)
		line += "\x1b[%sm%s \x1b[0m" % (style, char)
	return line


def text_color(text, color):
	if color:
		text = color + text + color0
	return text


def Print(text, color=None, line=True):
	"""
	This function is needed to prevent errors
	like IOError: device is not ready 
	which is probably happens when script running under screen
	"""
	if (time.gmtime().tm_mon, time.gmtime().tm_mday) == (4, 1):
		text = use_lsd(text)
	elif color:
		text = text_color(text, color)
	if line:
		text += "\n"
	try:
		sys.stdout.write(text.decode("utf-8"))
		sys.stdout.flush()
	except (IOError, OSError):
		pass
