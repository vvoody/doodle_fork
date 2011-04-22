# -*- coding: utf-8 -*-

from hashlib import md5
import re

from google.appengine.api import users, memcache, mail
from google.appengine.ext import db, deferred

from setting import *
from common import *


class EntityNotFound(object):
	def __nonzero__(self):
		return False

ENTITY_NOT_FOUND = EntityNotFound()

EVENTUAL_CONSISTENCY_CONFIG = db.create_config(read_policy=db.EVENTUAL_CONSISTENCY)
QUICK_LIMITED_EVENTUAL_CONSISTENCY_CONFIG = db.create_config(deadline=0.5, read_policy=db.EVENTUAL_CONSISTENCY)

USER_FLAGS = {
	'active': 1, # 可用，未禁言
	'verified': 2, # 已验证
    'mute': 4 # 是否不接收邮件通知
}

class User(db.Model):
	# key name: email 邮箱
	name = db.StringProperty(required=True) # 用户名
	site = db.StringProperty(indexed=False) # 主页
	flag  = db.IntegerProperty(default=USER_FLAGS['active'] | USER_FLAGS['verified'], indexed=False) # 属性

	@staticmethod
	def get_current_user():
		current_user = users.get_current_user()
		return User.get_user_by_email(current_user.email()) if current_user else None

	@staticmethod
	@memcached('get_user_by_email', USER_CACHE_TIME, lambda email: email)
	def get_user_by_email(email):
		try:
			user = User.get_by_key_name(email)
			return user if user else User.get_or_insert(key_name=email, name=email.split('@', 1)[0])
		except:
			def save_user(email):
				User.get_or_insert(key_name=email, name=email.split('@', 1)[0])
			deferred.defer(save_user, email)
			return User(key_name=email, name=email.split('@', 1)[0])

	@memcached('has_graded', USER_CACHE_TIME, lambda self, article_key: '%s_%s' % (self.key().name(), article_key.id()))
	def has_graded(self, article_key):
		return Point.get_by_key_name(self.key().name(), article_key) or ENTITY_NOT_FOUND

	def grade_article(self, article_id, value):
		if not article_id:
			return None

		article = Article.get_article_by_id(article_id)
		if not article or not article.published:
			return None

		article_key = article.key()
		email = self.key().name()

		if Point.get_by_key_name(email, article_key): # should not use cached has_graded()
			return None
		else:
			def grade(article_key, value, email):
				article = Article.get(article_key)
				if not article:
					return
				if value:
					article.like += 1
				else:
					article.hate += 1
				article.put()
				Point(key_name=email, parent=article_key, value=value).put()
				memcache.set('has_graded:%s_%s' % (email, article_key.id()), True, USER_CACHE_TIME)
				return article.like, article.hate
			return db.run_in_transaction(grade, article_key, value, email)

	def get_gravatar(self, https=False):
		if https:
			return 'https://secure.gravatar.com/avatar/' + md5(self.key().name()).hexdigest()
		return 'http://www.gravatar.com/avatar/' + md5(self.key().name()).hexdigest()

	def status(self):
		flag = self.flag
		if not (flag & USER_FLAGS['active']):
			return u'禁言'
		elif flag & USER_FLAGS['verified']:
				return u'已验证'
		return u'未验证'


class Category(db.Model):
	# key name: 分类名
	path = db.StringProperty(required=True) # 分类路径，以CATEGORY_PATH_DELIMETER结束，如含父分类，也以它分隔

	_LIMIT = 1000 # 分类数应该不会超过1000

	def level(self): # 分类级别，1表示根分类，2为一级子类…
		return len(self.path.split(CATEGORY_PATH_DELIMETER)) - 1

	@memcached('get_sub_categories', CATEGORY_CACHE_TIME, lambda self, limit=_LIMIT: self.key().name())
	def get_sub_categories(self, limit=_LIMIT):
		path = self.path
		return Category.all().filter('path >', path).filter('path <', path + u'\ufffd').order('path').fetch(limit)

	def has_sub_categories(self):
		path = self.path
		return Category.all().filter('path >', path).filter('path <', path + u'\ufffd').count(1)

	@staticmethod
	@memcached('get_category_with_subs', CATEGORY_CACHE_TIME, lambda path, limit=_LIMIT: hash(path))
	def get_category_with_subs(path, limit=_LIMIT):
		return Category.all().filter('path >=', path).filter('path <', path + u'\ufffd').order('path').fetch(limit)

	@staticmethod
	@memcached('get_all_categories', CATEGORY_CACHE_TIME)
	def get_all_categories(limit=_LIMIT):
		return Category.all().order('path').fetch(limit)

	@memcached('get_articles_in_category', ARTICLES_CACHE_TIME,
			   lambda self, cursor=None, fetch_limit=ARTICLES_PER_PAGE:
				('%s_%s' % (self.key().name(), cursor)) if cursor else self.key().name())
	def get_articles(self, cursor=None, fetch_limit=ARTICLES_PER_PAGE):
		path = self.path
		query = Article.all().filter('published =', True).filter('category >=', path).filter('category <', path + u'\ufffd')
		return get_fetch_result_with_valid_cursor(query_with_cursor(query, cursor), fetch_limit, config=EVENTUAL_CONSISTENCY_CONFIG)

	@staticmethod
	def fill_pathes(path):
		if not path:
			return []
		names = path.split(CATEGORY_PATH_DELIMETER)
		each_path = ''
		all_pathes = []
		for name in names:
			name = name.strip()
			if not name:
				continue
			each_path += name + CATEGORY_PATH_DELIMETER
			all_pathes.append((each_path, name))
		return all_pathes

	@staticmethod
	def path_to_name(path):
		if path:
			return path.rstrip(CATEGORY_PATH_DELIMETER).rsplit(CATEGORY_PATH_DELIMETER, 1)[-1]
		return ''


def move_articles_between_categories(from_path, to_path):
	articles = Article.all().filter('category =', from_path).fetch(100)
	if not articles:
		mail.send_mail_to_admins(ADMIN_EMAIL, u'批量更改文章分类成功', u'源分类：%s\n目标分类：%s' % (from_path, to_path))
		return
	for article in articles:
		article.category = to_path
	db.put(articles)
	deferred.defer(move_articles_between_categories, from_path, to_path)

def delete_category(path):
	articles = Article.all().filter('category =', path).fetch(100)
	if not articles:
		db.delete(db.Key.from_path('Category', Category.path_to_name(path)))
		clear_categories_memcache()
		mail.send_mail_to_admins(ADMIN_EMAIL, u'删除分类成功', u'分类路径：' + path)
		return
	for article in articles:
		article.category = None
	db.put(articles)
	deferred.defer(delete_category, path)

def generate_categories(categories=None, cursor=None):
	if not categories:
		categories = set()
	query = Article.all()
	articles = query_with_cursor(query, cursor).fetch(100)
	categories |= set([article.category for article in articles])

	if len(articles) == 100:
		deferred.defer(generate_categories, categories, query.cursor())
	elif categories:
		category_pathes = []
		category_names = []
		for category in list(categories):
			if category and len(article.category) >= 2 and article.category[-1] == CATEGORY_PATH_DELIMETER:
				category_pathes.append(category)
				category_names.append(Category.path_to_name(category))
		if category_pathes:
			categories = Category.get_by_key_name(category_names)
			new_categories = [Category(key_name=category_name, path=category_path) for category_name, category_path, category in izip(category_names, category_pathes, categories) if not category]
			db.put(new_categories)
			clear_categories_memcache()


class Tag(db.Model):
	# key name: 标签名
	count = db.IntegerProperty(default=0) # 文章数

	_LIMIT = 1000 # 标签数应该不会超过1000

	@memcached('get_articles_in_tag', ARTICLES_CACHE_TIME,
			   lambda self, cursor=None, fetch_limit=ARTICLES_PER_PAGE:
				('%s_%s' % (self.key().name(), cursor)) if cursor else self.key().name())
	def get_articles(self, cursor=None, fetch_limit=ARTICLES_PER_PAGE):
		query = Article.all().filter('tags =', self.key().name()).filter('published =', True)
		return get_fetch_result_with_valid_cursor(query_with_cursor(query, cursor), fetch_limit, config=EVENTUAL_CONSISTENCY_CONFIG)

	@staticmethod
	@memcached('get_all_tags', TAGS_CACHE_TIME)
	def get_all_tags(limit=_LIMIT):
		return Tag.all().fetch(limit)

	def update_count(self):
		self.count = Article.all().filter('tags =', self.key().name()).filter('published =', True).count(None)
		self.put()
		return self.count


def move_articles_between_tags(from_name, to_name):
	articles = Article.all().filter('tags =', from_name).fetch(100)
	if not articles:
		from_tag = Tag.get_by_key_name(from_name)
		if from_tag:
			from_tag.count = 0
			from_tag.put()

		to_tag = Tag.get_by_key_name(to_name)
		if to_tag:
			to_tag.update_count()

		mail.send_mail_to_admins(ADMIN_EMAIL, u'批量更改文章标签成功', u'源标签：%s\n目标标签：%s' % (from_name, to_name))
		return
	for article in articles:
		tags = article.tags
		while from_name in tags:
			tags.remove(from_name)
		if to_name not in tags:
			tags.append(to_name)
		article.tags = tags
	db.put(articles)
	deferred.defer(move_articles_between_tags, from_name, to_name)

def delete_tag(name):
	articles = Article.all().filter('tags =', name).fetch(100)
	if not articles:
		db.delete(db.Key.from_path('Tag', name))
		clear_tags_memcache()
		mail.send_mail_to_admins(ADMIN_EMAIL, u'删除标签成功', u'标签名：' + name)
		return
	for article in articles:
		tags = article.tags
		while name in tags:
			tags.remove(name)
		article.tags = tags
	db.put(articles)
	deferred.defer(delete_tag, name)

def generate_tags(tags=None, cursor=None):
	if not tags:
		tags = set()
	query = Article.all()
	articles = query_with_cursor(query, cursor).fetch(100)

	new_tags = []
	for article in articles:
		if article.tags:
			new_tags += article.tags
	tags |= set(new_tags)

	if len(articles) == 100:
		deferred.defer(generate_tags, tags, query.cursor())
	elif tags:
		tag_names = list(tags)
		tags = Tag.get_by_key_name(tags)
		new_tags = [Tag(key_name=tag_name) for tag_name, tag in izip(tag_names, tags) if not tag]
		db.put(new_tags)
		clear_tags_memcache()

def update_tags_count():
	tags = Tag.get_all_tags()
	if tags:
		for tag in tags:
			tag.count = Article.all().filter('tags =', tag.key().name()).filter('published =', True).count(None)
		db.put(tags) # 由于标签数一般不会太多，所以就不分成多个任务来执行了

CONTENT_FORMAT_FLAG = {
	'plain': 0,
    'bbcode': 1,
    'html': 2
}

def _cache_articles(articles, published):
	size = len(articles)
	if size:
		last = size - 1
		mapping = {}
		for i in xrange(size):
			article = articles[i]
			id = article.key().id()
			mapping['get_article_by_url:%s' % hash(article.url)] = article
			mapping['get_article_by_id:%s' % id] = article
			if i > 0:
				mapping['get_next_article:%s_%s' % (id, published)] = articles[i - 1]
			if i < last:
				mapping['get_previous_article:%s_%s' % (id, published)] = articles[i + 1]
		memcache.set_multi(mapping, ARTICLE_CACHE_TIME)


class Article(db.Model):
	# key id
	title = db.StringProperty(required=True) # 标题
	url = db.StringProperty(required=True) # 相对链接
	content = db.TextProperty() # 内容
	format = db.IntegerProperty(default=CONTENT_FORMAT_FLAG['plain'], indexed=False) # 解析格式
	published = db.BooleanProperty(default=True) # 是否对外发布
	time = db.DateTimeProperty(auto_now_add=True) # 发布时间
	mod_time = db.DateTimeProperty(auto_now_add=True) # 修改时间
	keywords = db.StringListProperty() # 搜索关键字，保存为小写
	tags = db.StringListProperty() # 标签
	category = db.StringProperty() # 分类路径
	hits = db.IntegerProperty(default=0) # 点击数
	replies = db.IntegerProperty(default=0) # 评论数
	like = db.IntegerProperty(default=0) # 喜欢评价数
	hate = db.IntegerProperty(default=0) # 讨厌评价数
	rating = db.ComputedProperty(lambda self: (self.like or 0) - (self.hate or 0))
	# password = db.StringProperty(indexed=False)
	# view_level = db.IntegerProperty(default=0, indexed=False)
	# closed = db.BooleanProperty(default=False, indexed=False) #  是否关闭评论

	_PATTERN = re.compile(r'\d{4}/\d{2}/\d{2}/.+')

	@staticmethod
	@memcached('get_articles_for_homepage', ARTICLES_CACHE_TIME,
				lambda cursor=None, fetch_limit=ARTICLES_PER_PAGE: hash(cursor) if cursor else None)
	def get_articles_for_homepage(cursor=None, fetch_limit=ARTICLES_PER_PAGE):
		query = Article.all().filter('published =', True).order('-time')
		articles, cursor = get_fetch_result_with_valid_cursor(query_with_cursor(query, cursor), fetch_limit, config=EVENTUAL_CONSISTENCY_CONFIG)
		_cache_articles(articles, True)
		return articles, cursor

	@staticmethod
	def get_unpublished_articles(cursor=None, fetch_limit=ARTICLES_PER_PAGE):
		query = Article.all().filter('published =', False).order('-mod_time')
		articles, cursor = get_fetch_result_with_valid_cursor(query_with_cursor(query, cursor), fetch_limit)
		_cache_articles(articles, False)
		return articles, cursor

	@staticmethod
	@memcached('get_articles_for_feed', FEED_CACHE_TIME)
	def get_articles_for_feed(fetch_limit=ARTICLES_PER_PAGE):
		return Article.all().filter('published =', True).order('-mod_time').fetch(fetch_limit)

	@staticmethod
	@memcached('get_article_by_url', ARTICLE_CACHE_TIME, lambda url: hash(url))
	def get_article_by_url(url):
		if len(url) <= 500:
			article = Article.all().filter('url =', url).get(config=EVENTUAL_CONSISTENCY_CONFIG)
			if article:
				memcache.set('get_article_by_id:%s' % article.key().id(), article, ARTICLE_CACHE_TIME)
				return article
		return ENTITY_NOT_FOUND

	@staticmethod
	@memcached('get_article_by_id', ARTICLE_CACHE_TIME, lambda id: id)
	def get_article_by_id(id):
		if id > 0:
			article = Article.get_by_id(id)
			if article:
				memcache.set('get_article_by_url:%s' % hash(article.url), article, ARTICLE_CACHE_TIME)
				return article
		return ENTITY_NOT_FOUND

	def category_name(self):
		return Category.path_to_name(self.category)

	def html_summary(self):
		format = self.format
		content = self.content
		if SUMMARY_DELIMETER.search(content):
			summary = SUMMARY_DELIMETER.split(content, 1)[0]
		elif SUMMARY_DELIMETER2.search(content):
			summary = SUMMARY_DELIMETER2.split(content, 1)[0]
		else:
			summary = content
		if format & CONTENT_FORMAT_FLAG['bbcode']:
			return convert_bbcode_to_html(summary, escape=not(format & CONTENT_FORMAT_FLAG['html']))
		if format & CONTENT_FORMAT_FLAG['html']:
			return summary
		else:
			return parse_plain_text(summary)

	def html_content(self):
		format = self.format
		content = self.content
		if SUMMARY_DELIMETER.search(content):
			content = SUMMARY_DELIMETER.sub('', content, 1)
		elif SUMMARY_DELIMETER2.search(content):
			content = SUMMARY_DELIMETER2.split(content, 1)[1]

		if format & CONTENT_FORMAT_FLAG['bbcode']:
			return convert_bbcode_to_html(content, escape=not(format & CONTENT_FORMAT_FLAG['html']))
		if format & CONTENT_FORMAT_FLAG['html']:
			return content
		else:
			return parse_plain_text(content)

	def previous_article(self, published):
		previous_article = None
		try:
			previous_article = Article.all().filter('published =', published).filter('time <', self.time).order('-time').get(config=QUICK_LIMITED_EVENTUAL_CONSISTENCY_CONFIG)
			if previous_article:
				memcache.set_multi({
					'get_previous_article:%s_%s' % (self.key().id(), published): previous_article,
					'get_next_article:%s_%s' % (previous_article.key().id(), published): self,
					'get_article_by_url:%s' % hash(previous_article.url): previous_article,
					'get_article_by_id:%s' % previous_article.key().id(): previous_article
				}, ARTICLE_CACHE_TIME)
				return previous_article
			memcache.set('get_previous_article:%s_%s' % (self.key().id(), published), ENTITY_NOT_FOUND, ARTICLE_CACHE_TIME)
			return ENTITY_NOT_FOUND
		except:
			return previous_article

	def next_article(self, published):
		next_article = None
		try:
			next_article = Article.all().filter('published =', published).filter('time >', self.time).order('time').get(config=QUICK_LIMITED_EVENTUAL_CONSISTENCY_CONFIG)
			if next_article:
				memcache.set_multi({
					'get_next_article:%s_%s' % (self.key().id(), published): next_article,
					'get_previous_article:%s_%s' % (next_article.key().id(), published): self,
					'get_article_by_url:%s' % hash(next_article.url): next_article,
					'get_article_by_id:%s' % next_article.key().id(): next_article
				}, ARTICLE_CACHE_TIME)
				return next_article
			memcache.set('get_next_article:%s_%s' % (self.key().id(), published), ENTITY_NOT_FOUND, ARTICLE_CACHE_TIME)
			return ENTITY_NOT_FOUND
		except:
			return next_article

	def nearby_articles(self, published=True):
		key = '%s_%s' % (self.key().id(), published)
		previous_key = 'get_previous_article:' + key
		next_key = 'get_next_article:' + key
		nearby_articles = memcache.get_multi((next_key, previous_key))

		previous_article = nearby_articles.get(previous_key, None)
		if previous_article is None:
			previous_article = self.previous_article(published)

		next_article = nearby_articles.get(next_key, None)
		if next_article is None:
			next_article = self.next_article(published)
		return previous_article, next_article

	@staticmethod
	@memcached('relative_articles', ARTICLES_CACHE_TIME, lambda id, limit: id)
	def relative_articles(id, limit):
		if id <= 0:
			return []
		article = Article.get_article_by_id(id)
		if not article:
			return []
		article_key = article.key()
		keywords = article.keywords
		relative_article_keys = set()
		left = limit
		total = 0
		if keywords:
			# 居然遇到这个问题：Keys only queries do not support IN filters.
			for keyword in keywords:
				relative_article_keys |= set(Article.all(keys_only=True).filter('keywords =', keyword).filter('published =', True).fetch(left + 1))
				relative_article_keys.discard(article_key)
				total = len(relative_article_keys)
				if total >= limit:
					return db.get(list(relative_article_keys)[:limit])
			left -= total
		tags = article.tags
		if tags:
			for tag in tags:
				new_article_keys = set(Article.all(keys_only=True).filter('tags =', tag).filter('published =', True).fetch(left + 1)) - relative_article_keys
				new_article_keys.discard(article_key)
				if len(new_article_keys) >= left:
					return db.get(list(relative_article_keys) + list(new_article_keys)[:left])
				relative_article_keys |= new_article_keys
			left = limit - len(relative_article_keys)
		category = article.category
		if category:
			new_article_keys = set(Article.all(keys_only=True).filter('category >=', category).filter('category <', category + u'\ufffd').filter('published =', True).fetch(left + 1)) - relative_article_keys
			new_article_keys.discard(article_key)
			if len(new_article_keys) >= left:
				return db.get(list(relative_article_keys) + list(new_article_keys)[:left])
			relative_article_keys |= new_article_keys
		if relative_article_keys:
			return db.get(relative_article_keys)
		return []

	@staticmethod
	def calc_hits(article_id):
		if article_id < 0:
			return False
		def calc(key):
			try:
				hits = memcache.get(key)
				if hits:
					hits = int(hits)
					if hits:
						article = Article.get_by_id(int(key.split(':')[1]))
						if article:
							article.hits += hits
							article.put()
							memcache.decr(key, hits)
				return True
			except:
				return False
		return db.run_in_transaction(calc, article_id)

	@staticmethod
	def calc_rating(article_id):
		if article_id < 0:
			return None
		article = Article.get_article_by_id(article_id)
		if not article:
			return None
		def calc(article_key):
			article = Article.get(article_key)
			if not article:
				return None
			article.like = Point.all().ancestor(article_key).filter('value =', True).count(None)
			article.hate = Point.all().ancestor(article_key).filter('value =', False).count(None)
			return like, hate
		return db.run_in_transaction(calc, article.key())

	@staticmethod
	def search(keywords, published, cursor=None, fetch_limit=ARTICLES_PER_PAGE):
		if not cursor:
			query = Article.all().filter('title =', keywords)
			if published is not None:
				query.filter('published =', published)
			article = query.fetch(1) # 一般不会写同名文章，有需要的自己增加这个数值
			if article:
				fetch_limit -= 1
		else:
			article = []
		if keywords:
			keywords = set(keywords.split())
			query = Article.all()
			for keyword in keywords:
				query.filter('keywords =', keyword.lower())
			if published is not None:
				query.filter('published =', published)
			articles, cursor = get_fetch_result_with_valid_cursor(query_with_cursor(query, cursor), fetch_limit)
			return (article + articles, cursor)
		else:
			return article, None

	def quoted_url(self):
		return escape(quoted_string(self.url))

	def quoted_not_escaped_url(self):
		return quoted_string(self.url)


class Comment(db.Model):
	# parent: Article
	email = db.StringProperty(required=True) # 评论者邮箱
	content = db.TextProperty() # 内容
	format = db.IntegerProperty(default=CONTENT_FORMAT_FLAG['plain'], indexed=False) # 解析格式
	ua = db.StringListProperty(indexed=False) # 用户代理信息
	time = db.DateTimeProperty(auto_now_add=True) # 发表时间

	@staticmethod
	# get_comments_with_user_by_article_key更为常用，不需要cache 2次
	def get_comments_by_article_key(article_key, order=True, cursor=None, fetch_limit=COMMENTS_PER_PAGE):
		query = Comment.all().ancestor(article_key).order('time' if order else '-time')
		return get_fetch_result_with_valid_cursor(query_with_cursor(query, cursor), fetch_limit, config=EVENTUAL_CONSISTENCY_CONFIG)

	@staticmethod
	@memcached('get_comments_with_user_by_article_key', COMMENTS_CACHE_TIME,
			   lambda article_key, order=True, cursor=None, fetch_limit=COMMENTS_PER_PAGE:
				('%s_%s_%s' % (article_key.id(), order, cursor)))
	def get_comments_with_user_by_article_key(article_key, order=True, cursor=None, fetch_limit=COMMENTS_PER_PAGE):
		comments = Comment.get_comments_by_article_key(article_key, order, cursor, fetch_limit)
		user_keys = [db.Key.from_path('User', comment.email) for comment in comments[0]]
		return comments, db.get(user_keys, config=EVENTUAL_CONSISTENCY_CONFIG)

	@staticmethod
	def get_comment_by_id(comment_id, article_id):
		return Comment.get_by_id(comment_id, db.Key.from_path('Article', article_id))

	def html_content(self):
		format = self.format
		content = self.content
		if format & CONTENT_FORMAT_FLAG['bbcode']:
			return convert_bbcode_to_html(content, escape=not(format & CONTENT_FORMAT_FLAG['html']))
		if format & CONTENT_FORMAT_FLAG['html']:
			return content
		else:
			return parse_plain_text(content)

	@staticmethod
	@memcached('latest_comments', 0, lambda limit: limit)
	def latest_comments(limit):
		comments = Comment.all().order('-time').fetch(limit)
		articles = db.get([comment.parent_key() for comment in comments])
		users = db.get([db.Key.from_path('User', comment.email) for comment in comments])
		return comments, articles, users

def update_articles_replies(cursor=None):
	query = query_with_cursor(Article.all(), cursor)
	articles = query.fetch(100)
	if articles:
		for article in articles:
			article.replies = Comment.all().ancestor(article).count(None)
		db.put(articles)
	if len(articles) < 100:
		mail.send_mail_to_admins(ADMIN_EMAIL, u'文章评论数更新完成', u'您可以去检查看看了')
	else:
		deferred.defer(update_articles_replies, query.cursor())

def update_article_replies(article_key):
	def update(article_key):
		article = Article.get(article_key)
		if article:
			article.replies = Comment.all().ancestor(article_key).count(None)
			article.put()
	db.run_in_transaction(update, article_key)

def delete_comments_of_user(email, article_keys=None, cursor=None):
	query = Comment.all(keys_only=True).filter('email =', email)
	comment_keys = query_with_cursor(query, cursor).fetch(100)
	if not article_keys:
		article_keys = set()
	if comment_keys:
		db.delete(comment_keys)
		article_keys |= set([comment_key.parent() for comment_key in comment_keys])
	if len(comment_keys) == 100:
		deferred.defer(delete_comments_of_user, email, article_keys, query.cursor())
	else:
		clear_latest_comments_memcache()
		for article_key in article_keys:
			deferred.defer(update_article_replies, article_key)


class Sitemap(db.Model):
	# key id
	content = db.TextProperty()

	_LIMIT = 1000

	@staticmethod
	def fill(id, cursor=None, fetch_limit=_LIMIT):
		query = Article.all().filter('published =', True)
		articles = query_with_cursor(query, cursor).fetch(fetch_limit)
		if articles:
			content = engine.render('sitemap.xml', {'articles': articles})
			Sitemap(key=db.Key.from_path('Sitemap', id), content=content).put()
			return len(articles), query.cursor()
		return 0, None

	@staticmethod
	@memcached('get_sitemap', SITEMAP_CACHE_TIME)
	def get_sitemap():
		sitemaps = Sitemap.all().fetch(Sitemap._LIMIT)
		xml = ['<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
		for sitemap in sitemaps:
			xml.append(sitemap.content)
		xml.append('</urlset>')
		return ''.join(xml)


class Point(db.Model):
	# key name: User email
	# parent: Article
	value = db.BooleanProperty(required=True) # 喜欢或讨厌


class Feed(db.Model):
	content = db.TextProperty() # 内容
	cursor = db.StringProperty(indexed=False) # 游标
	time = db.DateTimeProperty(auto_now_add=True) # 生成时间


class Subscriber(db.Model):
	# key name: ua
	count = db.IntegerProperty(default=1, indexed=False) # 订阅数
	time = db.DateTimeProperty(auto_now=True) # 最后抓取时间

def set_subscriber(user_agent, count):
	if len(user_agent) > 500:
		user_agent = user_agent[:500]
	key = 'get_subscriber:' + user_agent
	try:
		if memcache.get(key) != count:
			Subscriber(key_name=user_agent, count=count).put()
			memcache.set(key, count, SUBSCRIBER_CACHE_TIME)
	except:
		pass

@memcached('get_subscribers', SUBSCRIBERS_CACHE_TIME)
def get_subscribers():
	subscribers = Subscriber.all().fetch(1000)
	if subscribers:
		return reduce(lambda x, y: x + y.count, subscribers, 0)
	return 0


class Twitter(db.Model):
	name = db.StringProperty(indexed=False)
	token = db.StringProperty(indexed=False)
	secret = db.StringProperty(indexed=False)

@memcached('get_twitter')
def get_twitter():
	return Twitter.get_by_id(1) or ENTITY_NOT_FOUND

def set_twitter(**kw):
	try:
		twitter = Twitter(key=db.Key.from_path('Twitter', 1), **kw)
		twitter.put()
		memcache.set('get_twitter', twitter)
		return True
	except:
		return False
