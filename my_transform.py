# -*- coding: utf-8 -*-

from cgi import escape
from datetime import *
from hashlib import md5
import logging
from re import compile as reg_compile
import time

from google.appengine.ext import db
from google.appengine.ext.bulkload import transform

from common import formatted_date_for_url
from model import CONTENT_FORMAT_FLAG
from setting import CATEGORY_PATH_DELIMETER


def import_timestamp(timestamp):
	return datetime.utcfromtimestamp(int(timestamp))

def export_timestamp(dt):
	return int(time.mktime(dt.timetuple()))

def import_key_from_id(kind):
	def make_key(id):
		return db.Key.from_path(kind, int(id))
	return make_key

def import_key_from_parent_and_id(parent_kind, kind):
	def make_key(ids):
		parent_id, id = ids.split(' ', 1)
		return db.Key.from_path(parent_kind, int(parent_id), kind, int(id))
	return make_key

def import_user_key_from_parent_and_email(parent_and_email):
	parent_id, email = parent_and_email.split(' ', 1)
	return db.Key.from_path('Article', int(parent_id), 'User', email)

def import_user_key_from_email(email):
	return db.Key.from_path('User', email)

def import_string_list(string, delimeter=', '):
	return string.split(delimeter)

def parse_url(s):
	parts = s.split(' ', 2)
	return parts[0].replace('-', '/') + '/' + parts[2]

def parse_url2(s):
	timestamp, title = s.split(' ', 1)
	dt = datetime.utcfromtimestamp(int(timestamp))
	return dt.strftime('%Y/%m/%d/') + title

def parse_format(formats):
	formats = formats.split()
	return (int(formats[0]) and CONTENT_FORMAT_FLAG['html']) | (not int(formats[1]) and CONTENT_FORMAT_FLAG['bbcode'])

def join_list(list):
	return ','.join(list) if list else ''

def to_list(string):
	return string.split(',') if string else []

HTML_TAG_PATTERN = reg_compile('<.*?>')
BBCODE_TAG_PATTERN = reg_compile(r'\[.*?\]')

def break_content_to_summary(content, format, size):
	if format & CONTENT_FORMAT_FLAG['bbcode']:
		content = BBCODE_TAG_PATTERN.sub(' ', content)
	if format == 0:
		content = escape(content)
	content = HTML_TAG_PATTERN.sub(' ', content)[:size].strip()
	amp_position = content[-6:].rfind('&')
	if amp_position > -1:
		content = content[:len(content) - 6 + amp_position]
	return content

def parse_summary(size, flag):
	def break_content(content):
		return db.Text(break_content_to_summary(content, flag, int(size)))
	return break_content

def parse_url3(timestamp, title):
	dt = datetime.utcfromtimestamp(int(timestamp))
	return formatted_date_for_url(dt) + title

def parse_format2(htmlon, bbcodeoff):
	return (int(htmlon) and CONTENT_FORMAT_FLAG['html']) | (not int(bbcodeoff) and CONTENT_FORMAT_FLAG['bbcode'])


class Article(db.Model):
	title = db.StringProperty()
	url = db.StringProperty()
	content = db.TextProperty()
	format = db.IntegerProperty(default=0, indexed=False)
	published = db.BooleanProperty(default=True)
	time = db.DateTimeProperty(auto_now_add=True)
	mod_time = db.DateTimeProperty(auto_now_add=True)
	keywords = db.StringListProperty()
	tags = db.StringListProperty()
	category = db.StringProperty()
	hits = db.IntegerProperty(default=0)
	replies = db.IntegerProperty(default=0)
	like = db.IntegerProperty(default=0)
	hate = db.IntegerProperty(default=0)
	rating = db.IntegerProperty(default=0)

def generate_article(input_dict, instance, bulkload_state_copy):
	category = input_dict.get('name', None)
	keywords = [category] if category else []
	return Article(key=db.Key.from_path('Article', int(input_dict['tid'])), title=input_dict['subject'],
		url=parse_url3(input_dict['dateline'], input_dict['subject']), content=input_dict['message'],
		format=parse_format2(input_dict['htmlon'], input_dict['bbcodeoff']), published=True,
		time=import_timestamp(input_dict['dateline']), mod_time=import_timestamp(input_dict['dateline']),
		keywords=keywords, tags=keywords, category=category + CATEGORY_PATH_DELIMETER if category else None, hits=int(input_dict['views']), replies=int(input_dict['replies']))

def generate_article2(input_dict, instance, bulkload_state_copy):
	time = transform.import_date_time('%Y-%m-%d %H:%M:%S')(input_dict['post_date_gmt'])
	mod_time = transform.import_date_time('%Y-%m-%d %H:%M:%S')(input_dict['post_modified_gmt'])
	return Article(key=db.Key.from_path('Article', int(input_dict['ID'])), title=input_dict['post_title'],
		url=formatted_date_for_url(time) + input_dict['post_name'], content=input_dict['post_content'], format=2,
		published=(input_dict['post_status'] == 'publish'), time=time, mod_time=mod_time, keywords=[], tags=[],
		category=None, replies=int(input_dict['comment_count']))

class Comment(db.Model):
	email = db.StringProperty()
	content = db.TextProperty()
	format = db.IntegerProperty(default=0, indexed=False)
	time = db.DateTimeProperty(auto_now_add=True)

def generate_comment(input_dict, instance, bulkload_state_copy):
	return Comment(key=db.Key.from_path('Article', int(input_dict['tid']), 'Comment', int(input_dict['pid'])),
	    email=input_dict['email'], content=input_dict['message'], format=parse_format2(input_dict['htmlon'], input_dict['bbcodeoff']),
		time=import_timestamp(input_dict['dateline']))

def generate_comment2(input_dict, instance, bulkload_state_copy):
	return Comment(key=db.Key.from_path('Article', int(input_dict['comment_post_ID']),
		'Comment', int(input_dict['comment_ID'])),
	    email=input_dict['comment_author_email'], content=input_dict['comment_content'], format=2,
		time=transform.import_date_time('%Y-%m-%d %H:%M:%S')(input_dict['comment_date_gmt']))

class User(db.Model):
	name = db.StringProperty()
	site = db.StringProperty(indexed=False)
	flag  = db.IntegerProperty(default=3, indexed=False)

def generate_user(input_dict, instance, bulkload_state_copy):
	return User(key_name=input_dict['email'], name=input_dict['username'], site=input_dict['site'], flag=3)

def generate_user2(input_dict, instance, bulkload_state_copy):
	return User(key_name=input_dict['comment_author_email'], name=input_dict['comment_author'],
	    site=input_dict['comment_author_url'], flag=3)
