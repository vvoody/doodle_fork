# -*- coding: utf-8 -*-


import logging
from time import time

from google.appengine.api import apiproxy_stub_map

request_arrive_time = 0
db_count = 0
db_time = 0
db_start_time = 0

def before_db(service, call, request, response):
	global db_count, db_start_time
	db_count += 1
	db_start_time = time()

def after_db(service, call, request, response):
	global db_time
	dt = time() - db_start_time
	db_time += dt
	if dt > 1:
		logging.warning('This request took %s seconds.' % dt)
		logging.warning(request)

apiproxy_stub_map.apiproxy.GetPreCallHooks().Append('before_db', before_db, 'datastore_v3')
apiproxy_stub_map.apiproxy.GetPostCallHooks().Push('after_db', after_db, 'datastore_v3')