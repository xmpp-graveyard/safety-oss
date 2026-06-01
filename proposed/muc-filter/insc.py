# coding: utf-8

if DefLANG in ("RU", "UA"):
	AnsBase_temp = {key: value.decode("utf-8") for key, value in {
		"ENABLED": "включена",
		"DISABLED": "отключена",
		"config": "something: %s",
		"": "",
		"": "",
		"": "",
		"": "",
		"": "",
		"": "",
		"": ""
	}.iteritems()}

	Obscene = "(?:бляд", u"\sблят", u"\sбля\s", u"\sблять\s", u"\sплять\s", u"хуй", u"\sибал", u"\sебал", u"\sхуи", u"хуител", u"хуя", u"\sхую", u"\sхуе", u"\sахуе", u"\sохуе", u"хуев", u"хер", u"\sпох\s", u"\sнах\s", u"писд", u"пизд", u"рizd", u"\sпздц\s", u"\sеб", u"\sепана\s", u"\sепать\s", u"\sипать\s", u"\sвыепать\s", u"\sибаш", u"\sуеб", u"проеб", u"праеб", u"приеб", u"съеб", u"взъеб", u"взьеб", u"въеб", u"вьеб", u"выебан", u"перееб", u"недоеб", u"долбоеб", u"долбаеб", u"\sниибац", u"\sнеебац", u"\sнеебат", u"\sниибат", u"\sпидар", u"\sрidаr", u"\sпидар", u"\sпидор", u"педор", u"пидор", u"пидарас", u"пидараз", u"\sпедар", u"педри", u"пидри", u"\sзаеп", u"\sзаип", u"\sзаеб", u"ебучий", u"ебучка\s", u"епучий", u"епучка\s", u"\sзаиба", u"заебан", u"заебис", u"\sвыеб", u"выебан", u"\sпоеб", u"\sнаеб", u"\sнаеб", u"сьеб", u"взьеб", u"вьеб", u"\sгандон", u"\sгондон", u"пахуи", u"похуис", u"\sманда\s", u"мандав", u"залупа", u"\sзалупог)".decode("utf-8")
else:
	AnsBase_temp = {
		"ENABLED": "Enabled",
		"DISABLED": "Disabled",
		"pvlock": "\n[pvlock] Private lock: ",
		"censor": "\n[censor] Censor filter: ",
		"lnick": "\n[lnick] Blocked nick length: %s",
		"adv": "\n[adv] Advertisement block: ",
		"lmsg": "\n[lmsg] Blocked message length: %s",
		"history": "\n[history] Block joins with no history: ",
		"repeat": "\n[repeat] Repeat messages count to kick: %s",
		"lstat": "\n[lstat] Blocked status length: %s",
		"lres": "\n[lres] Blocked resource length: %s",
		"pastebin": "\n[pastebin] Message length will be posted to pastebin: %s",
		"fastjoin": "\n[fastjoin] Block fast joins/nick changes: ",
		"fastmsg": "\n[fastmsg] Time between 3 messages causes kick: %s",
		"same": "\n[same] Number of similar sentences causes ban: %s",
		"mention": "\n[mention] Limit of user mentions: %s",
		"china": "\n[china] Anti-china mode: ",
		"pattern": "\n[pattern] Pattern integration: ",
		"history_block": "%s: No history found.",
		"lnick_block": "Large nick block!",
		"lres_block": "Large resource block!",
		"cens_block": "Censor block!",
		"common_block": "%s: You're blocked by some reason. No matter what is it. Just go to hell.",
		"adv_block": "%s: Advertisement.",
		"pv_block": "Private locked.",
		"user_pv_block": "User's private locked.",
		"repeat_block": "Message repeat!",
		"lmsg_block": "%s: Message length!",
		"fastjoin_block": "%s: Fastjoin!",
		"fastmsg_block": "%s: Too fast message sending!",
		"same_block": "%s: Same messages block!",
		"pv_filter": ["Your private already filtered", "Your private not filtered.", "Your private locked.", "Your private isn't locked.", "Your personal private messages filter is ENABLED.", "Your personal private messages filter is DISABLED."],
		"pmlock": "\n[pmlock] Your personal private messages filter: ",
		"china_block": "%s: China block!",
		"mention_block": "%s: Mention limit!",
		"caps_block": "%s: Caps blocked!",
		"pattern_block": "%s: blocked by pattern!",
		"nickchange": "\n[nickchange] Replacing user nicknames: ",
		"vercheck": "\n[vercheck] Vercheck integration: "

	}

	Obscene = [u"bitch", u"shit", u"conference", u"www", u"http", u"fuck", u"whore", u"شرموط", u"نايک", u"امک", u"أمک", u"اختک", u"أختک", u"أهلک", u"اهلک", u"أهلک", u"تنتاك", u"متناك", u"منتاك", u"نايك", u"فاشخ", u"كسمك", u"منيوك", u"قحبه", u"قحبة", u"إالحس", u"طيزى", u"طيزي", u"إيري", u"إيرى", u"زوبري", u"زوبرى", u"دعاره", u"دعارة", u"أختك", u"عرصا", u"يلعن", u"أمك", u"اختك", u"نىايك", u"ممحون", u"سحاقيه", u"سحاقية", u"ايري", u"بكسك", u"لكسك", u"أيري", u"حميانه", u"حميانه", u"مدام", u"مطلقه", u"مطلقة", u"منيوك", u"ممحون", u"ضهري", u"ضهرك", u"تلحس", u"موجب", u"بندوق", u"دعار", u"أختك", u"قوط", u"يلعن", u"أختك", u"سحاق", u"درزي", u"ترضع", u"لواط", u"طياز", u"بزاز", u"فخاد", u"فخاذ", u"حميان", u"حمار", u"تافه", u"طيز", u"اسدي", u"الاسد", u"باخىتك", u"الىشىرمىوطىه", u"القىحبىه", u"ايىري", u"اخىتك", u"تنتاك", u"متناك", u"منتاك", u"نايك", u"فاشخ", u"كسمك", u"منيوك", u"قحبه", u"قحبة", u"إالحس", u"طيزى", u"طيزي", u"إيري", u"إيرى", u"زوبري", u"زوبرى", u"دعاره", u"دعارة", u"أختك", u"زورونا", u"زورونى", u"زوروني", u"نورونا", u"شرفونا", u"عرصا", u"يلعن", u"أمك", u"اختك", u"ممحون", u"رومنـ", u"أنضمو", u"انضمو", u"إنضمو", u"شرفتونا", u"سحاقيه", u"سحاقية", u"ايري", u"بكسك", u"لكسك", u"أيري", u"حميانه", u"حميانه", u"مدام", u"مطلقه", u"مطلقة", u"منيوك", u"ممحون", u"ضهري", u"ضهرك", u"تلحس", u"موجب", u"بندوق", u"دعار", u"أختك", u"قوط", u"يلعن", u"سحاق", u"درزي", u"ترضع", u"حميان", u"عراعير", u"مندسين", u"الأسد", u"شبيح", u"مسيره", u"مسيرة", u"مظاهره", u"مظاهرة", u"الجيش", u"الاسد", u"أسدى", u"أسدي", u"عرعور", u"مندس", u"يسقط", u"مؤيد", u"جيش", u"جنود", u"نظام", u"مسير", u"حرية", u"ثورة", u"ثوره", u"اسدى", u"اسدي", u"قطر", u"بثار", u"سقط", u"سقاط", u"سنى", u"سني", u"علوى", u"علوي", u"شيعي", u"شيعى", u"دمـ»ـاسـ»ـكـ»ـس", u"نـ»ـايـ»ـك", u"نـ»ـايـ»ـك", u"أخـ»ـتـ»ـك", u"أمـ»ـك", u"فـ»ـاتـ»ـح", u"شـ»ـرفـ»ـك", u"كـ»ـس", u"اخـ»ـتـ»ـك", u"اخـ»ـتـ»ـك", u"اناصهرك", u"اناصهر", u"كافر", u"اخت", u"أخت", u"جامبو", u"جامبوالجبار", u"عائشه", u"عائشة", u"ابوبكر", u"الخطاب", u"عمرالخطاب", u"عمروالخطاب", u"نا.يك", u"ونا.يك", u"ر.ضعو", u"خوا.تكن", u"خواتكن", u"ـــــــ", u"فاتـح", u"ينيك"]
