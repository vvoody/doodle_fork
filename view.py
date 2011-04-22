# -*- coding: utf-8 -*-

import logging
from re import compile as reg_compile

import simplejson
from google.appengine.api import mail, memcache
import yui

from common import UserHandler, incr_counter, unquoted_cursor
from model import *
from setting import *


class HomePage(UserHandler):
	@yui.server_cache(ARTICLES_CACHE_TIME, True, True, True)
	def get(self):
		cursor = unquoted_cursor(self.GET['cursor'])
		articles, next_cursor = Article.get_articles_for_homepage(cursor)
		self.echo('home.html', {
			'articles': articles,
			'next_cursor': next_cursor,
			'title': BLOG_TITLE,
			'cursor': cursor,
			'page': 'home'
		})


class ArticlePage(UserHandler):
	def get(self, url):
		article = Article.get_article_by_url(path_to_unicode(url))
		if article and (article.published or self.request.is_admin):
			if self.is_spider():
				self.response.set_last_modified(article.mod_time)
			user = self.request.current_user
			self.echo('article.html', {
				'article': article,
				'can_grade': user and user.flag & USER_FLAGS['active'] and not user.has_graded(article.key()),
				'title': article.title,
				'page': 'article'
			})
			incr_counter('article_counter:%s' % article.key().id(), BLOG_ADMIN_RELATIVE_PATH + 'article_counter/')
		else:
			self.error(404)
			self.echo('error.html', {
				'page': '404',
				'title': '找不到该文章',
				'h2': '糟糕',
				'msg': '好像弄丢了什么东东，完全找不到了的说…'
			})


class RelativeArticlesJson(UserHandler):
	@yui.server_cache(ARTICLES_CACHE_TIME, False)
	@yui.client_cache(ARTICLES_CACHE_TIME, 'public')
	def get(self, id):
		self.set_content_type('json')
		relative_articles = Article.relative_articles(int(id), RELATIVE_ARTICLES)
		if not relative_articles:
			return

		relative_articles.sort(cmp=lambda x, y: cmp(x.hits + x.rating * 10, y.hits + y.rating * 10), reverse=True)
		article_list = []
		for article in relative_articles:
			article_list.append({
				'title': escape(article.title),
				'url': article.quoted_url()
			})
		self.write(simplejson.dumps(article_list))

	def display_exception(self, exception):
		self.write(simplejson.dumps({
			'status': 500,
			'content': u'服务器出错了，您可以尝试重试，或报告管理员。'
		}))


class CommentPage(UserHandler):
	#@yui.server_cache(COMMENTS_CACHE_TIME)
	def get(self, id, cursor=None):
		article =  Article.get_article_by_id(int(id))
		if article:
			(comments, next_cursor), users = Comment.get_comments_with_user_by_article_key(
				article.key(), cursor=unquoted_cursor(cursor))
			self.echo('comment.html', {
				'comments': comments,
				'next_cursor': next_cursor,
				'comment_users': users,
				'id': id,
			    'article': article,
				'title': u'%s - 评论页' % article.title,
				'page': 'comments'
			})
		else:
			self.error(404)
			self.echo('error.html', {
				'page': '404',
				'title': '找不到该评论页',
				'h2': '找不到该评论页',
				'msg': '请检查URL是否输入错误。'
			})

	@yui.authorized()
	def post(self, id, cursor=None):
		if self.GET['viewmode'] == 'mobile':
			error_page = message_page = 'message_mobile.html'
		else:
			error_page = 'error.html'
			message_page = 'message.html'
		is_ajax = self.request.is_xhr
		if is_ajax:
			self.set_content_type('json')
		user = self.request.current_user
		is_admin = self.request.is_admin
		if not (is_admin or user.flag & USER_FLAGS['active']):
			if is_ajax:
				self.write(simplejson.dumps({
					'status': 403,
					'content': u'抱歉，您已被管理员禁言，无法发表评论。如有异议，请联系管理员。'
				}))
			else:
				self.echo(error_page, {
					'page': 'error',
					'title': '评论发表失败',
					'h2': '抱歉，您已被管理员禁言，无法发表评论',
					'msg': '如有异议，请联系管理员。'
				})
			return
		comment = self.POST.get('comment').strip()
		if not comment:
			if is_ajax:
				self.write(simplejson.dumps({
					'status': 400,
					'content': u'拜托，你也写点内容再发表吧'
				}))
			else:
				self.echo(error_page, {
					'page': 'error',
					'title': '评论发表失败',
					'h2': '拜托，你也写点内容再发表吧',
					'msg': '赶紧返回重新写吧…'
				})
			return

		ua = []
		browser, platform, os, os_version, vendor = self.request.ua_details
		if platform:
			if platform in ('iPhone', 'iPod Touch', 'iPad', 'Android'):
				ua.append(platform)
			elif self.request.is_mobile:
				ua.append('mobile')
		else:
			if self.request.is_mobile:
				ua.append('mobile')
			elif os and os in ('Windows', 'Mac OS', 'Linux', 'FreeBSD'):
				ua.append(os)
		if browser:
			if browser == 'Internet Explorer':
				ua.append('IE')
			elif browser in ('Firefox', 'Chrome', 'Safari', 'Opera'):
				ua.append(browser)
			elif browser == 'Mobile Safari':
				ua.append('Safari')
			elif browser in ('Opera Mini', 'Opera Mobile'):
				ua.append('Opera')

		article = Article.get_article_by_id(int(id))
		if article:
			def post_comment(article_key, email, content, format, ua):
				comment = Comment(parent=article_key, email=email, content=content, format=format, ua=ua)
				comment.put()
				article = Article.get(article_key)
				article.replies += 1
				article.put()
				return comment
			email = user.key().name()
			format = CONTENT_FORMAT_FLAG['bbcode'] if self.POST['bbcode'] == 'on' else CONTENT_FORMAT_FLAG['plain']
			comment = db.run_in_transaction(post_comment, article.key(), email, comment, format, ua)
			if comment:
				if is_ajax:
					self.write(simplejson.dumps({
						'status': 200,
						'comment': {
							'user_name': user.name,
							'url': user.site,
							'img': user.get_gravatar(),
							'ua': comment.ua,
							'time': formatted_time(comment.time),
							'id': comment.key().id(),
							'content': comment.html_content()
						}
					}))
				else:
					self.echo(message_page, {
						'page': 'message',
						'title': '评论发表成功',
						'h2': '评论发表成功',
						'msg': '缓存更新后将会立即显示您的评论'
					})
				try:
					clear_latest_comments_memcache(id)
					deferred.defer(ping_hubs, BLOG_COMMENT_FEED_URL)
					url = ''
					if NOTIFY_WHEN_REPLY and not is_admin and (not SEND_INTERVAL or memcache.add('has_sent_email_when_reply', 1, SEND_INTERVAL)):
						url = u'%s%s%s' % (MAJOR_HOST_URL, BLOG_HOME_RELATIVE_PATH, article.quoted_url())
						html_content = comment.html_content()[:4096] # maximum size of an AdminEmailMessage is 16 kilobytes
						html_body = u'%s 在 <a href="%s">%s</a> 评论道:<br/>%s' % (escape(user.name), url, article.title, html_content)
						title = u'Re: ' + article.title
						mail.AdminEmailMessage(sender=ADMIN_EMAIL, subject=title, html=html_body).send()
						import gdata_for_gae
						deferred.defer(gdata_for_gae.send_sms, user.name, article.title)
					if MAX_SEND_TO and format != CONTENT_FORMAT_FLAG['plain'] and  (is_admin or user.flag & SEND_LEVEL):
						if not url:
							url = u'%s%s%s' % (MAJOR_HOST_URL, BLOG_HOME_RELATIVE_PATH, article.quoted_url())
							html_content = comment.html_content()[:4096] # maximum size of parameters of a task queue is 10 kilobytes
							html_body = u'%s 在 <a href="%s">%s</a> 评论道:<br/>%s<hr/>您收到这封邮件是因为有人回复了您的评论。您可前往原文回复，请勿直接回复该邮件。<br/>若您不希望被打扰，可修改您的<a href="%s%sprofile/">账号设置</a>。' % (escape(user.name), url, article.title, html_content, MAJOR_HOST_URL, BLOG_HOME_RELATIVE_PATH)
							title = u'Re: ' + article.title
						else:
							html_body = u'%s<hr/>您收到这封邮件是因为有人回复了您的评论。您可前往原文回复，请勿直接回复该邮件。<br/>若您不希望被打扰，可修改您的<a href="%s%sprofile/">账号设置</a>。' % (html_body, MAJOR_HOST_URL, BLOG_HOME_RELATIVE_PATH)
						deferred.defer(send_reply_notification, html_content, html_body, title, int(id))
				except:
					logging.error(format_exc())
			else:
				if is_ajax:
					self.write(simplejson.dumps({
						'status': 500,
						'content': u'评论发表失败，原文不存在或数据库忙'
					}))
				else:
					self.echo(error_page, {
						'page': 'error',
						'title': '评论发表失败',
						'h2': '糟糕',
						'msg': '评论发表失败，原文不存在或数据库忙'
					})
		else:
			if is_ajax:
				self.write(simplejson.dumps({
					'status': 404,
					'content': u'评论发表失败，原文不存在'
				}))
			else:
				self.echo(error_page, {
					'page': 'error',
					'title': '评论发表失败',
					'h2': '糟糕',
					'msg': '评论发表失败，原文不存在'
				})


class CommentJson(UserHandler):
	#@yui.server_cache(COMMENTS_CACHE_TIME, False)
	def get(self, id, cursor=None):
		self.set_cache(0)
		self.set_content_type('json')

		(comments, next_cursor), users = Comment.get_comments_with_user_by_article_key(
				db.Key.from_path('Article', int(id)), self.GET['order'] != 'desc', cursor=unquoted_cursor(cursor))
		comments_list = []
		for comment, user in izip(comments, users):
			comments_list.append({
				'user_name': user.name,
				'url': escape(user.site) if user.site else '',
				'img': user.get_gravatar(),
				'ua': comment.ua,
				'time': formatted_time(comment.time),
				'id': comment.key().id(),
				'content': comment.html_content()
			})
		self.write(simplejson.dumps({
			 'next_cursor': next_cursor,
			 'comments': comments_list
		}))

	def display_exception(self, exception):
		self.write(simplejson.dumps({
			'status': 500,
			'content': u'服务器出错了，您可以尝试重试，或报告管理员。'
		}))


class PointPage(UserHandler):
	@yui.authorized()
	def get(self, id, value):
		self.set_cache(0)
		is_ajax = self.request.is_xhr
		value = bool(int(value))
		user = self.request.current_user

		if user.flag == USER_FLAGS['active']:
			if is_ajax:
				self.write(simplejson.dumps({
					'success': 0
				}))
			else:
				self.echo('error.html', {
					'page': 'error',
					'title': '评分失败',
					'h2': '糟糕',
					'msg': '你被管理员禁止评分了'
				})
			return

		point = user.grade_article(int(id), value)
		if point:
			if is_ajax:
				self.write(simplejson.dumps({
					'success': 1,
					'like': point[0],
					'hate': point[1]
				}))
			else:
				self.echo('message.html', {
					'page': 'message',
					'title': '评分成功',
					'h2': '评分成功',
					'msg': '赶紧去评别的文章吧'
				})
		else:
			if is_ajax:
				self.write(simplejson.dumps({
					'success': 0
				}))
			else:
				self.echo('error.html', {
					'page': 'error',
					'title': '评分失败',
					'h2': '糟糕',
					'msg': '你人品真差，评分失败了'
				})


class PreviewPage(UserHandler):
	@yui.authorized()
	def post(self):
		data = self.POST['data']
		self.write(convert_bbcode_to_html(data).encode('utf-8'))


class TagPage(UserHandler):
	def get(self, name):
		name = path_to_unicode(name)
		memcache_key = 'get_tag_by_name:' + name
		tag = memcache.get(memcache_key)
		if tag is None:
			tag = Tag.get_by_key_name(name) or ENTITY_NOT_FOUND
		memcache.set(memcache_key, tag, TAGS_CACHE_TIME)
		if tag:
			cursor = unquoted_cursor(self.GET['cursor'])
			articles, next_cursor = tag.get_articles(cursor)
			self.echo('tag.html', {
				'title': u'标签《%s》' % name,
				'tag_name': name,
				'articles': articles,
				'next_cursor': next_cursor,
				'cursor': cursor,
				'page': 'tag'
			})
		else:
			self.error(404)
			self.echo('error.html', {
				'page': '404',
				'title': '找不到该标签',
				'h2': '糟糕',
				'msg': '好像弄丢了什么东东，完全找不到了的说…'
			})


class CategoryPage(UserHandler):
	def get(self, name):
		name = path_to_unicode(name)
		memcache_key = 'get_category_by_name:' + name
		category = memcache.get(memcache_key)
		if category is None:
			category = Category.get_by_key_name(name) or ENTITY_NOT_FOUND
		memcache.set(memcache_key, category, CATEGORY_CACHE_TIME)
		if category:
			cursor = unquoted_cursor(self.GET['cursor'])
			articles, next_cursor = category.get_articles(cursor)
			self.echo('category.html', {
				'title': u'分类《%s》' % name,
				'category_name': name,
				'articles': articles,
				'next_cursor': next_cursor,
				'cursor': cursor,
				'page': 'category'
			})
		else:
			self.error(404)
			self.echo('error.html', {
				'page': '404',
				'title': '找不到该分类',
				'h2': '糟糕',
				'msg': '好像弄丢了什么东东，完全找不到了的说…'
			})


class SearchPage(UserHandler):
	def get(self):
		request = self.request
		GET = request.GET
		keywords = GET['keywords']
		if keywords:
			keywords = keywords.strip()
		if keywords:
			cursor = unquoted_cursor(GET['cursor'])
			articles, next_cursor = Article.search(keywords, None if request.is_admin else True, cursor)
			self.echo('search.html', {
				'title': '搜索结果',
				'articles': articles,
				'next_cursor': next_cursor,
				'keywords': keywords,
				'cursor': cursor,
				'page': 'search'
			})
		else:
			self.echo('message.html', {
				'page': 'message',
				'title': '请输入搜索关键字',
				'h2': '连关键字都没有，你搜索啥啊？',
				'msg': '填几个关键字再试试吧'
			})


class ProfilePage(UserHandler):
	@yui.authorized()
	def get(self):
		self.echo('profile.html', {
			'title': '账号设置',
			'page': 'profile'
		})

	@yui.authorized()
	def post(self):
		POST = self.POST
		user = self.request.current_user
		is_ajax = self.request.is_xhr

		try:
			user.name = POST['name']
			site = (POST['site'] or '').strip()
			if site:
				if site[:4] == 'www.':
					site = 'http://' + site
				if '%' in site:
					user.site = site
				else:
					user.site = quoted_url(site)
			else:
				user.site = None
			if POST['mute'] == 'on':
				if not (user.flag & USER_FLAGS['mute']):
					user.flag |= USER_FLAGS['mute']
			elif user.flag & USER_FLAGS['mute']:
				user.flag &= ~USER_FLAGS['mute']
			user.put()
			memcache.set('get_user_by_email:' + user.key().name(), user, USER_CACHE_TIME)
			if is_ajax:
				self.write('您的资料保存成功了')
			else:
				self.echo('message.html', {
					'page': 'message',
					'title': '用户资料保存成功',
					'h2': '看上去没出什么错呢',
					'msg': '您的资料保存成功了'
				})
		except (db.TransactionFailedError, db.InternalError, db.Timeout):
			if is_ajax:
				self.write('由于服务器忙或超时，您的资料保存失败了')
			else:
				self.error(500)
				self.echo('error.html', {
					'page': '500',
					'title': '用户资料保存失败',
					'h2': '糟糕',
					'msg': '由于服务器忙或超时，您的资料保存失败了'
				})
		except:
			if is_ajax:
				self.write('怎么说你呢，参数都填错了…')
			else:
				self.error(400)
				self.echo('error.html', {
					'page': '400',
					'title': '用户资料保存失败',
					'h2': '怎么说你呢，参数都填错了…',
					'msg': '请返回重填吧'
				})


class RedirectToHomePage(yui.RequestHandler):
	@yui.client_cache(ARTICLES_CACHE_TIME, 'public')
	def get(self):
		self.redirect(BLOG_HOME_RELATIVE_PATH, 301)


class RedirectToArticlePage(yui.RequestHandler):
	@yui.client_cache(ARTICLE_CACHE_TIME, 'public')
	def get(self, tid=''):
		if not tid:
			try:
				id = int(self.GET['tid'])
			except:
				self.redirect(BLOG_HOME_RELATIVE_PATH, 301)
				return
		else:
			id = int(tid)

		article = Article.get_article_by_id(id)
		if article:
			self.redirect(BLOG_HOME_RELATIVE_PATH + article.quoted_not_escaped_url(), 301)
		else:
			self.redirect(BLOG_HOME_RELATIVE_PATH, 301)


class RedirectToHomeOrArticlePage(yui.RequestHandler):
	_PATTERN = reg_compile(r'tid-(\d+)(?:-page-\d+)?.html')

	@yui.client_cache(ARTICLE_CACHE_TIME, 'public')
	def get(self):
		match = RedirectToHomeOrArticlePage._PATTERN.match(self.request.query_string)
		if match:
			article = Article.get_article_by_id(int(match.group(1)))
			if article:
				self.redirect(BLOG_HOME_RELATIVE_PATH + article.quoted_not_escaped_url(), 301)
				return
		self.redirect('/', 301)


class FeedPage(BaseHandler):
	def get(self):
		self.set_content_type('atom')
		user_agent = self.request.user_agent.replace(',gzip(gfe)', '')
		subscribers = get_subscribers_from_ua(user_agent)
		if subscribers:
			if 'Feedfetcher-Google' in user_agent:
				user_agent = user_agent.replace(' %s subscribers;' % subscribers, '') # 避免重复统计
		else:
			user_agent = '%s:%s' % (self.request.client_ip, user_agent)
			subscribers = 1
		set_subscriber(user_agent, subscribers)

		articles = Article.get_articles_for_feed()
		if articles:
			last_modified = articles[0].mod_time
			last_updated = iso_time_format(last_modified)
		else:
			last_modified = datetime.utcnow()
			last_updated = iso_time_now()
		self.response.set_last_modified(last_modified)
		self.echo('feed.xml', {'articles': articles, 'last_updated': last_updated})


class GeneratedFeedPage(BaseHandler):
	# 只用于一次导入大批feed
	def get(self):
		self.set_content_type('atom')
		feed = Feed.all().order('-time').get()
		if feed:
			self.write(feed.content.encode('utf-8'))
			if 'Feedfetcher-Google' in self.request.user_agent:
				url = u'%s%sgenerate_feed?cursor=%s' % (self.request.host_url, BLOG_ADMIN_RELATIVE_PATH, feed.cursor)
				mail.send_mail_to_admins(ADMIN_EMAIL, u'Feedfetcher-Google已抓取feed',
					u'确认Google Reader已收录后，可点此链接继续生成后续feed：\n' + url,
					html=u'确认Google Reader已收录后，可点此<a href="%s">链接</a>继续生成后续feed。' % url)


class CommentFeedPage(BaseHandler):
	def get(self):
		self.set_content_type('atom')
		comments, articles, users = Comment.latest_comments(LATEST_COMMENTS_FOR_FEED)
		if comments:
			last_modified = comments[0].time
			last_updated = iso_time_format(last_modified)
		else:
			last_modified = datetime.utcnow()
			last_updated = iso_time_now()
		self.response.set_last_modified(last_modified)
		self.echo('comment_feed.xml', {'comments': comments, 'articles': articles, 'users': users, 'last_updated': last_updated})


class SitemapPage(yui.RequestHandler):
	@yui.client_cache(SITEMAP_CACHE_TIME, 'public')
	def get(self):
		self.set_content_type('text/xml')
		self.write(Sitemap.get_sitemap())


class RedirectToFeedPage(yui.RequestHandler):
	@yui.client_cache(FEED_CACHE_TIME, 'public')
	def get(self):
		self.redirect(BLOG_FEED_URL, 301)


class WapHomePage(BaseHandler):
	@yui.server_cache(ARTICLES_CACHE_TIME, False)
	@yui.client_cache(ARTICLES_CACHE_TIME, 'public')
	def get(self):
		cursor = unquoted_cursor(self.GET['cursor'])
		articles, next_cursor = Article.get_articles_for_homepage(cursor)
		self.echo('home_mobile.html', {
			'articles': articles,
			'next_cursor': next_cursor,
			'title': BLOG_TITLE,
			'cursor': cursor,
			'page': 'home'
		})


class WapArticlePage(UserHandler):
	def get(self, url):
		article = Article.get_article_by_url(path_to_unicode(url))
		if article and (article.published or self.request.is_admin):
			self.echo('article_mobile.html', {
				'article': article,
				'title': article.title,
				'page': 'article'
			})
			incr_counter('article_counter:%s' % article.key().id(), BLOG_ADMIN_RELATIVE_PATH + 'article_counter/')
		else:
			self.error(404)
			self.echo('message_mobile.html', {
				'page': '404',
				'title': '找不到该文章',
				'h2': '找不到该文章',
				'msg': '请检查URL是否输入错误。'
			})


class WapCommentPage(UserHandler):
	#@yui.server_cache(COMMENTS_CACHE_TIME)
	def get(self, id, cursor=None):
		article =  Article.get_article_by_id(int(id))
		if article:
			(comments, next_cursor), users = Comment.get_comments_with_user_by_article_key(
				article.key(), cursor=unquoted_cursor(cursor))
			self.echo('comment_mobile.html', {
				'comments': comments,
				'next_cursor': next_cursor,
				'comment_users': users,
				'id': id,
			    'article': article,
				'title': u'%s - 评论页' % article.title,
				'page': 'comments'
			})
		else:
			self.error(404)
			self.echo('message_mobile.html', {
				'page': '404',
				'title': '找不到该评论页',
				'h2': '找不到该评论页',
				'msg': '请检查URL是否输入错误。'
			})


class RedirectToWapHomePage(yui.RequestHandler):
	@yui.client_cache(86400, 'public')
	def get(self):
		self.redirect(BLOG_HOME_RELATIVE_PATH + 'wap/', 301)


class RobotsPage(BaseHandler):
	@yui.client_cache(3600, 'public')
	def get(self):
		self.set_content_type('text/plain')
		self.echo('robots.txt')


class RobotsMobilePage(BaseHandler):
	@yui.client_cache(3600, 'public')
	def get(self):
		self.set_content_type('text/plain')
		self.echo('robots_mobile.txt')


class NotFoundPage(BaseHandler):
	@yui.client_cache(600, 'public')
	def get(self):
		self.error(404)
		self.echo('error.html', {
			'page': '404',
			'title': '找不到该这个网址',
			'h2': '糟糕',
			'msg': '好像弄丢了什么东东，完全找不到了的说…'
		})

	post = get


class NotFoundMobilePage(BaseHandler):
	@yui.client_cache(600, 'public')
	def get(self):
		self.error(404)
		self.echo('message_mobile.html', {
			'page': '404',
			'title': '找不到该这个网址',
			'h2': '糟糕',
			'msg': '好像弄丢了什么东东，完全找不到了的说…'
		})

	post = get

class WarmupPage(yui.RequestHandler):
	def get(self):
		Category.get_all_categories()
		Tag.get_all_tags()
		Article.get_articles_for_homepage()
		Comment.latest_comments(LATEST_COMMENTS_FOR_SIDEBAR)
		get_subscribers()
		get_recent_tweets()


class LoginoutPage(yui.RequestHandler):
	def get(self):
		if self.request.user:
			self.redirect(users.create_logout_url(self.request.referer or BLOG_HOME_RELATIVE_PATH))
		else:
			self.redirect(users.create_login_url(self.request.referer or BLOG_HOME_RELATIVE_PATH))


class VerifySubscription(yui.RequestHandler):
	def get(self):
		verify_token = self.GET['hub.verify_token']
		if verify_token and verify_token == memcache.get('hub_verify_token'):
			memcache.delete('hub_verify_token')
			self.write(self.GET['hub.challenge'])
			mail.send_mail_to_admins(ADMIN_EMAIL, u'PubSubHubbub请求验证成功', u'验证参数为：\n%s' % dict(self.GET))
		else:
			logging.warning(u'PubSubHubbub请求验证失败，验证参数为：\n%s' % dict(self.GET))

	def post(self):
		pass
