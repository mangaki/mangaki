create:
	cd mangaki && ./manage.py makemessages --locale fr
	cd mangaki && ./manage.py makemessages --locale ja
	cd mangaki && ./manage.py makemessages --locale zh_Hant
	cd mangaki && ./manage.py makemessages --locale zh_Hans
	po-to-xls -o test.xlsx fr:mangaki/mangaki/locale/fr/LC_MESSAGES/django.po ja:mangaki/mangaki/locale/ja/LC_MESSAGES/django.po zh-hans:mangaki/mangaki/locale/zh_Hans/LC_MESSAGES/django.po zh-hant:mangaki/mangaki/locale/zh_Hant/LC_MESSAGES/django.po
	open test.xlsx

compile:
	xls-to-po fr test2.xlsx mangaki/mangaki/locale/fr/LC_MESSAGES/django.po
	xls-to-po ja test2.xlsx mangaki/mangaki/locale/ja/LC_MESSAGES/django.po
	xls-to-po zh-hant test2.xlsx mangaki/mangaki/locale/zh_Hant/LC_MESSAGES/django.po
	xls-to-po zh-hans test2.xlsx mangaki/mangaki/locale/zh_Hans/LC_MESSAGES/django.po
	cd mangaki && ./manage.py compilemessages
