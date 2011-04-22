# -*- coding: utf-8 -*-

import logging
import time
from traceback import format_exc

import atom
import gdata.auth
import gdata.calendar
import gdata.calendar.service
from gdata.alt.appengine import *

from setting import *


class Token(db.Model):
	token = db.BlobProperty()
	feed = db.StringProperty(indexed=False)


def save_auth_token(token, user=None, url=None):
	if user is None:
		user = users.get_current_user()
		if user:
			user = user.email()
	if user is None:
		return None
	if url is None:
		url = 'http://www.google.com/calendar/feeds/default/private/full'
	pickled_token = pickle.dumps(token)
	token = Token(key_name=user, token=pickled_token, feed=url)
	memcache.set('Token:' + user, token)
	return token.put()


def load_auth_token(user=None):
	if not user:
		user = users.get_current_user()
		if user:
			user = user.email()
	if not user:
		return None
	token = memcache.get('Token:' + user)
	if token:
		return token
	token = Token.get_by_key_name(user)
	if token:
		memcache.set('Token:' + user, token)
		return token
	return None


def del_auth_token(user=None):
	if not user:
		user = users.get_current_user()
		if user:
			user = user.email()
	if user:
		db.delete(db.Key.from_path('Token', user))
		memcache.delete('Token:' + user)


class AppEngineTokenStore(atom.token_store.TokenStore):
	def __init__(self, user=None, url=None):
		self.user = user
		self.url = url

	def add_token(self, token):
		if not hasattr(token, 'scopes') or not token.scopes:
			return False
		return bool(save_auth_token(token, self.user, self.url))

	def find_token(self, url):
		token = load_auth_token(self.user)
		if token:
			if not url:
				url = token.feed
			if url:
				if isinstance(url, (str, unicode)):
					url = atom.url.parse_url(url)
				token = pickle.loads(token.token)
				if token.valid_for_scope(url):
					return token
				else:
					del_auth_token(self.user)
		return atom.http_interface.GenericToken()

	def remove_token(self, token):
		token = Token.get_by_key_name(self.user)
		if token:
			token.delete()
		memcache.delete(self.user)
		return bool(token)

	def remove_all_tokens(self):
		del_auth_token(self.user)


def run_on_appengine(gdata_service, store_tokens=True,
		single_user_mode=False, deadline=None, user=None, url=None):
	gdata_service.http_client = AppEngineHttpClient(deadline=deadline)
	gdata_service.token_store = AppEngineTokenStore(user, url)
	gdata_service.auto_store_tokens = store_tokens
	gdata_service.auto_set_current_token = single_user_mode
	return gdata_service

def programmatic_login(email, password):
	try:
		client = gdata.calendar.service.CalendarService(email, password)
		client.ProgrammaticLogin()
		return client
	except:
		return None

def send_sms(name, title):
	try:
		if ADMIN_PASSWORD:
			calendar_client = programmatic_login(ADMIN_EMAIL, ADMIN_PASSWORD)
			feed = NOTIFY_FEED_URL
		else:
			token = load_auth_token(ADMIN_EMAIL)
			if not token:
				return
			feed = token.feed
	
			calendar_client = gdata.calendar.service.CalendarService()
			run_on_appengine(calendar_client, user=ADMIN_EMAIL)

		event_entry = gdata.calendar.CalendarEventEntry()
		event_entry.title = atom.Title(text=u'收到%s的评论' % name)
		start_time = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime(time.time() + 80))
		event_entry.when.append(gdata.calendar.When(start_time=start_time, reminder=gdata.calendar.Reminder(minutes=1, method='sms')))
		event_entry.where.append(gdata.calendar.Where(value_string=title))
		calendar_client.InsertEvent(event_entry, feed)
	except:
		logging.error(format_exc())
