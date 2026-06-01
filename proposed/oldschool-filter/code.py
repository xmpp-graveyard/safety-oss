# coding: utf-8
# Code © matrix.bz 2014 — 2015

MAX_MESSAGE_LENGTH = 800
QUEUE_TIMEOUT = 0.4#1.2

defaults = {"adv": True, "hash": False, "censor": True,
			"fastjoin": True, "history": True, "pvlock": False,
			"china": False, "pattern": False, "vercheck": False,

			"prlen": 256, "lnick": 30,
			"lmsg": 800, "fastmsg": 3,
			"pvlocks": [], "caps": [],
			"pastebin": 300,
			"repeat": 3, "lstat": 600,
			"lres": 40, "same": 3,
			"mention": 3, "nickchange": False}

CRIME_MESSAGES = ("I'm a suspect in crime!",
	"FBI investigates on me!",
	"CIA looking for me!",
	"DEA tracking me down!",
	"They got me! Oh My God, they got me!!!!!",
	"I got kidnapped by aliens last year!",
	"I've been to UFO!",
	"They let me out, until they investigate. But I'm innocent!",
	"I'm really innocent!")

#import platform
#import os
#if os.path.exists("BlackSmith.py"):
from mod_oldschool_filter import *
#elif platform.machine() == "x86_64":
#	from mod_filter_x64 import *
#else:
#	from mod_filter_x86 import *
