# -*- coding: utf-8 -*-

import logging
from email.header import decode_header
from email.utils import parseaddr
from itertools import izip
from random import random
from time import sleep

import simplejson
from google.appengine.ext import deferred
import yui

from common import UserHandler, incr_counter, timestamp_to_datetime, datetime_to_timestamp, unquoted_cursor
from model import *


class ArticleCounterTaskPage(yui.RequestHandler):
	def post(self):
		key = self.POST['key']
		retry_limit = 10
		while retry_limit > 0 and not Article.calc_hits(key):
			sleep(5)
			retry_limit -= 1


class AdminPage(yui.RequestHandler):
	def get(self):
		self.redirect(BLOG_ADMIN_RELATIVE_PATH + 'article/new/', 301)


class UnpublishedArticlesPage(BaseHandler):
	def get(self, cursor=None):
		cursor = unquoted_cursor(self.GET['cursor'])
		articles, next_cursor = Article.get_unpublished_articles(cursor)
		self.echo('unpublished_articles.html', {
			'cursor': cursor,
			'articles': articles,
		    'next_cursor': next_cursor,
		    'title': '未发布的文章',
		    'page': 'unpublished_article'
		})


class EditArticlePage(BaseHandler):
	def get(self, id):
		article = Article.get_by_id(int(id))
		if article:
			self.echo('edit_article.html', {
			    'article': article,
				'categories': Category.get_all_categories(),
				'tags': Tag.get_all_tags(),
				'title': u'编辑《%s》' % article.title,
				'page': 'edit_article'
			})
		else:
			self.write('该文章不存在')

	def post(self, id):
		article = Article.get_by_id(int(id))
		if not article:
			self.write('编辑失败，该文章不存在')
		request = self.request
		POST = self.POST
		data = dict(POST)
		data['title'] = (POST['title'] or '').strip()
		if not data['title']:
			self.write('编辑失败，标题不能为空')
			return

		data['time'] = get_time(data['time'], article.time)
		data['mod_time'] = get_time(data['mod_time'], article.mod_time)

		keywords = data['keywords'].split(',') if data['keywords'] else []
		data['keywords'] = [keyword.strip().lower() for keyword in keywords if keyword.strip()]
		tags = request.get_all('tags')
		if not tags or tags == ['']:
			data['tags'] = []
		else:
			data['tags'] = tags
		bbcode = POST['bbcode'] == 'on'
		html = POST['html'] == 'on'
		data['format'] = bbcode + 2 * html
		data['published'] = POST['published'] == 'on'

		old_url = article.url
		old_tags = set(article.tags)

		url = data['url']
		if not url:
			if REPLACE_SPECIAL_CHARACTERS_FOR_URL:
				data['url'] = formatted_date_for_url(data['time'] or article.time) + replace_special_characters_for_url(data['title'])
			else:
				data['url'] = formatted_date_for_url(data['time'] or article.time) + data['title']
		elif not Article._PATTERN.match(url):
			self.write('发表失败，链接格式不正确')
			return

		if url != old_url and Article.all().filter('url =', url).count(1):
			self.write('编辑失败，同链接的文章已存在')
			return

		def update(article_key, data):
			article = Article.get(article_key)
			if article:
				article.title = data['title']
				article.url = data['url']
				article.content = data['content']
				article.format = data['format']
				article.published = data['published']
				article.keywords = data['keywords']
				article.tags = data['tags']
				article.category = data['category'] or None
				if data['time']:
					article.time = data['time']
				if data['mod_time']:
					article.mod_time = data['mod_time']
				article.put()
				return article
			else:
				return None
		article = db.run_in_transaction(update, article.key(), data)

		if article:
			new_tags = set(article.tags)
			removed_tags = old_tags - new_tags
			added_tags = new_tags - old_tags

			if removed_tags:
				removed_tags = Tag.get_by_key_name(removed_tags)
				removed_tags = [removed_tag for removed_tag in removed_tags if removed_tag]
				for removed_tag in removed_tags:
					removed_tag.count -= 1
					if removed_tag.count < 0:
						removed_tag.count = 0

			if added_tags:
				added_tags = Tag.get_by_key_name(added_tags)
				added_tags = [added_tag for added_tag in added_tags if added_tag]
				for added_tag in added_tags:
					added_tag.count += 1

			changed_tags = set(removed_tags) | set(added_tags)
			if changed_tags:
				db.put(changed_tags)

			clear_article_memcache(id, old_url)
			quoted_url = article.quoted_url()
			full_url = MAJOR_HOST_URL + BLOG_HOME_RELATIVE_PATH + quoted_url
			if data['mod_time']:
				deferred.defer(ping_hubs, BLOG_FEED_URL)
				deferred.defer(ping_xml_rpc, full_url)
			if POST['twitter'] == 'on':
				deferred.defer(post_article_to_twitter, article.title, full_url)
			self.write('编辑成功，查看<a href="%s%s">更新后的文章</a>' % (BLOG_HOME_RELATIVE_PATH, quoted_url))
		else:
			self.write('编辑失败，文章已被删除或数据库忙')


class AddArticlePage(BaseHandler):
	def get(self):
		self.echo('new_article.html', {
		    'categories': Category.get_all_categories(),
		    'tags': Tag.get_all_tags(),
		    'title': '发表新文章',
		    'page': 'new_article'
		})

	def post(self):
		POST = self.POST
		title = strip(POST['title'])
		if not title:
			self.write('发表失败，标题不能为空')
			return
		time = parse_time(POST['time']) or datetime.utcnow()
		mod_time = parse_time(POST['mod_time']) or time
		url = strip(POST['url'])
		if not url:
			if REPLACE_SPECIAL_CHARACTERS_FOR_URL:
				url = formatted_date_for_url(time) + replace_special_characters_for_url(title)
			else:
				url = formatted_date_for_url(time) + title
		elif not Article._PATTERN.match(url):
			self.write('发表失败，链接格式不正确')
			return
		if Article.all().filter('url =', url).count(1):
			self.write('发表失败，同链接的文章已存在')
			return
		keywords = POST['keywords'].split(',') if POST['keywords'] else []
		keywords = [keyword.strip().lower() for keyword in keywords if keyword.strip()]
		tags = self.request.get_all('tags')
		if not tags or tags == ['']:
			tags = []
		published = POST['published'] == 'on'
		bbcode = POST['bbcode'] == 'on'
		html = POST['html'] == 'on'
		format = bbcode + 2 * html

		try:
			article = Article(
				title=title,
				url=url,
				content=POST['content'],
				format=format,
				published=published,
				keywords=keywords,
				tags=tags,
				category=POST['category'] or None,
				time=time,
				mod_time=mod_time
			)
			article.put()

			clear_article_memcache()
			deferred.defer(ping_hubs, BLOG_FEED_URL)
			quoted_url = article.quoted_url()
			full_url = MAJOR_HOST_URL + BLOG_HOME_RELATIVE_PATH + quoted_url
			deferred.defer(ping_xml_rpc, full_url)
			if POST['twitter'] == 'on':
				deferred.defer(post_article_to_twitter, article.title, full_url)
			self.write('发表成功，查看<a href="%s%s">发表后的文章</a>' % (BLOG_HOME_RELATIVE_PATH, quoted_url))
		except:
			self.write('发表失败，数据库出错或正忙')


class DeleteArticlePage(BaseHandler):
	def get(self, id):
		article = Article.get_by_id(int(id))
		if article:
			self.echo('del_article.html', {
				'page': 'del_article',
				'id': id,
			    'title': u'删除《%s》' % article.title
			})
		else:
			self.write('文章不存在，无需删除')

	def post(self, id):
		article = Article.get_by_id(int(id))
		if article:
			article_key = article.key()
			comments = Comment.all(keys_only=True).ancestor(article_key).fetch(500)
			while comments:
				db.delete(comments)
				comments = Comment.all(keys_only=True).ancestor(article_key).fetch(500)

			points = Point.all(keys_only=True).ancestor(article_key).fetch(500)
			while points:
				db.delete(points)
				points = Point.all(keys_only=True).ancestor(article_key).fetch(500)
			article.delete()
			clear_article_memcache(article_key.id(), article.url)
			clear_latest_comments_memcache(id)
			self.write('删除成功')
		else:
			self.write('文章不存在，无需删除')


class AddCategoryPage(BaseHandler):
	def get(self):
		self.echo('new_category.html', {
			'title': '添加新分类',
			'page': 'new_category'
		})

	def post(self):
		path_with_name = Category.fill_pathes(self.POST['path'])
		if not path_with_name:
			self.write('添加失败，分类不能为空')
			return

		try:
			for each_path, name in path_with_name:
				if Category.all().filter('path =', each_path).count(1):
					continue
				category = Category.get_by_key_name(name)
				if category and category.path != each_path:
					self.write((u'添加失败，分类名“%s”已存在于路径“%s”中' % (name, category.path)).encode('utf-8'))
					return
				Category.get_or_insert(key_name=name, path=each_path)
			clear_categories_memcache()
			self.write('添加成功')
		except:
			self.write('添加失败，数据库出错或正忙')


class RemoveCategoryPage(BaseHandler):
	def get(self):
		self.echo('del_category.html', {
			'categories': Category.get_all_categories(),
			'title': '删除分类',
			'page': 'del_category'
		})

	def post(self):
		path_with_name = Category.fill_pathes(self.POST['path'])
		if not path_with_name:
			self.write('删除失败，分类不能为空')
			return
		path, name = path_with_name[-1]
		category = Category.all().filter('path =', path).get()
		if not category:
			self.write('删除失败，分类不存在')
			return
		if category.has_sub_categories():
			self.write('删除失败，存在子分类，请先处理子分类')
			return

		deferred.defer(delete_category, path)
		self.write('清除任务添加成功，请暂时不要更改这个分类及其下的文章，直到您收到提示任务完成的邮件')


class MoveArticlesBetweenCategoriesPage(BaseHandler):
	def get(self):
		self.echo('move_category.html', {
			'categories': Category.get_all_categories(),
			'title': '批量更改文章分类',
			'page': 'move_category'
		})

	def post(self):
		from_pathes = Category.fill_pathes(self.POST['from_path'])
		if from_pathes:
			from_path, from_name = from_pathes[-1]
			from_category = Category.all().filter('path =', from_path).get()
			if not from_category:
				self.write('更改失败，源分类不存在')
				return
		else:
			self.write('更改失败，源分类不能为空')
			return

		to_pathes = Category.fill_pathes(self.POST['to_path'])
		if to_pathes:
			to_path, to_name = to_pathes[-1]
			if not Category.all().filter('path =', to_path).count(1):
				self.write('更改失败，目标分类不存在')
				return
		else:
			self.write('更改失败，目标分类不能为空')
			return

		if from_name == to_name:
			self.write('更改失败，源分类与目标分类相同')
			return

		deferred.defer(move_articles_between_categories, from_path, to_path)
		self.write('更改任务添加成功，请暂时不要更改这2个分类及其下的文章，直到您收到提示任务完成的邮件')


class AddTagPage(BaseHandler):
	def get(self):
		self.echo('new_tag.html', {
			'title': '添加新标签',
			'page': 'new_tag'
		})

	def post(self):
		name = strip(self.POST['name'])
		if not name:
			self.write('添加失败，标签名不能为空')
			return

		if Tag.get_or_insert(key_name=name):
			clear_tags_memcache()
			self.write('添加成功')
		else:
			self.write('添加失败，数据库出错或正忙')


class RemoveTagPage(BaseHandler):
	def get(self):
		self.echo('del_tag.html', {
			'tags': Tag.get_all_tags(),
			'title': '删除标签',
			'page': 'del_tag'
		})

	def post(self):
		name = strip(self.POST['name'])
		if not name:
			self.write('删除失败，标签名不能为空')
			return

		deferred.defer(delete_tag, name)
		self.write('删除任务添加成功，请暂时不要更改这个标签及其下的文章，直到您收到提示任务完成的邮件')


class MoveArticlesBetweenTagsPage(BaseHandler):
	def get(self):
		self.echo('move_tag.html', {
			'tags': Tag.get_all_tags(),
			'title': '批量更改文章标签',
			'page': 'move_tag'
		})

	def post(self):
		from_name = strip(self.POST['from_name'])
		if not from_name:
			self.write('更改失败，源标签名不能为空')
			return

		to_name = strip(self.POST['to_name'])
		if not to_name:
			self.write('更改失败，目标标签名不能为空')
			return

		if from_name == to_name:
			self.write('更改失败，源标签与目标标签相同')
			return

		to_tag = Tag.get_by_key_name(to_name)
		if not to_tag:
			self.write('更改失败，目标标签不存在')
			return

		deferred.defer(move_articles_between_tags, from_name, to_name)
		self.write('更改任务添加成功，请暂时不要更改这2个标签及其下的文章，直到您收到提示任务完成的邮件')


class DeleteCommentPage(BaseHandler):
	def get(self, article_id, comment_id):
		self.echo('del_comment.html', {
			'title': '删除评论',
			'page': 'del_comment'
		})

	def post(self, article_id, comment_id):
		def delete(article_id, comment_id):
			article = Article.get_by_id(article_id)
			if article:
				comment = Comment.get_by_id(comment_id, article)
				if comment:
					comment.delete()
					article.replies -= 1
					if article.replies < 0:
						article.replies = 0
					article.put()
		try:
			db.run_in_transaction(delete, int(article_id), int(comment_id))
			clear_latest_comments_memcache(article_id)
			if self.request.is_xhr:
				self.set_content_type('json')
				self.write(simplejson.dumps({'status': 204}))
			else:
				self.write('评论删除成功')
		except:
			if self.request.is_xhr:
				self.set_content_type('json')
				self.write(simplejson.dumps({
					'status': 500,
					'content': u'评论删除失败'
				}))
			else:
				self.write('评论删除失败')


class EditCommentPage(BaseHandler):
	def get(self, article_id, comment_id):
		comment = Comment.get_comment_by_id(int(comment_id), int(article_id))
		if comment:
			self.echo('edit_comment.html', {
			    'comment': comment,
				'title': '编辑评论',
				'page': 'edit_comment'
			})
		else:
			self.write('该评论不存在')

	def post(self, article_id, comment_id):
		comment = Comment.get_comment_by_id(int(comment_id), int(article_id))
		if comment:
			POST = self.POST
			comment.content = POST['content']
			bbcode = POST['bbcode'] == 'on'
			html = POST['html'] == 'on'
			comment.format = bbcode + 2 * html
			email = (POST['email'] or '').strip()
			if email and email != comment.email:
				User.get_user_by_email(email)
				comment.email = email
			time = get_time(POST['time'], comment.time)
			if time:
				comment.time = time
			uas = POST['ua'].split(',') if POST['ua'] else []
			comment.ua = [ua.strip() for ua in uas if ua.strip()]
			comment.put()
			clear_latest_comments_memcache(article_id)
			deferred.defer(ping_hubs, BLOG_COMMENT_FEED_URL)
			self.write('评论编辑成功')
		else:
			self.write('评论编辑失败，该评论不存在')


class SearchUserPage(BaseHandler):
	def get(self):
		GET = self.GET
		filter = GET['filter']
		value = GET['value']
		context = {
			'title': '搜索用户',
			'page': 'search_user',
		    'filer': filter,
		    'value': value
		}
		name = GET['name']
		if filter == 'email':
			user = User.get_by_key_name(value)
			context['users'] = [user] if user else []
		elif filter == 'name':
			users = User.all().filter('name =', value).fetch(100)
			context['users'] = users
		else:
			context['users'] = []
		self.echo('search_user.html', context)


class EditUserPage(BaseHandler):
	def get(self):
		GET = self.GET
		email = GET['email']
		if email:
			user = User.get_by_key_name(email)
			if user:
				self.echo('edit_user.html', {
					'user': user,
					'title': u'修改用户：%s' % user.name,
					'page': 'edit_user'
				})
			else:
				self.error(404)
				self.echo('error.html', {
					'page': '404',
					'title': '找不到该用户',
					'h2': '找不到该用户',
					'msg': '该用户或许已被删除。'
				})
		else:
			self.error(404)
			self.echo('error.html', {
				'page': '404',
				'title': '找不到该用户',
				'h2': '找不到该用户',
				'msg': '未提供用户的email'
			})

	def post(self):
		POST = self.POST
		email = POST['email']
		if email:
			user = User.get_by_key_name(email)
			if user:
				if POST['name']:
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
				flag = 0
				if POST['mute'] == 'on':
					flag |= USER_FLAGS['mute']
				if POST['verified'] == 'on':
					flag |= USER_FLAGS['verified']
				if POST['banned'] != 'on':
					flag |= USER_FLAGS['active']
				if POST['noua'] == 'on':
					flag |= USER_FLAGS['noua']
				user.flag = flag
				try:
					user.put()
					memcache.set('get_user_by_email:' + email, user, USER_CACHE_TIME)
					if POST['del-comment'] == 'on':
						deferred.defer(delete_comments_of_user, email)
					self.write('用户资料保存成功')
				except:
					self.write('用户资料保存失败')
			else:
				self.write('该用户不存在')
		else:
			self.write('未提供email信息，无法找到对应用户')


class EditUserByCommentPage(BaseHandler):
	def get(self, article_id, comment_id):
		comment = Comment.get_comment_by_id(int(comment_id), int(article_id))
		if comment:
			user = User.get_by_key_name(comment.email)
			if user:
				self.echo('edit_user.html', {
					'user': user,
					'title': u'编辑用户《%s》' % user.name,
					'page': 'edit_user'
				})
			else:
				self.error(404)
				self.echo('error.html', {
					'page': '404',
					'title': '找不到该用户',
					'h2': '找不到该用户',
					'msg': '该用户或许已被删除。'
				})
		else:
			self.error(404)
			self.echo('error.html', {
				'page': '404',
				'title': '相关评论已删除',
				'h2': '相关评论已删除',
				'msg': '无法找到该评论对应的用户'
			})


class GenerateSitemapPage(yui.RequestHandler):
	def get(self):
		id = self.GET['id']
		id = int(id) if id else 1
		num, next_cursor = Sitemap.fill(id, unquoted_cursor(self.GET['cursor']))
		if num == Sitemap._LIMIT: # 可能还没找到所有的
			taskqueue.add(queue_name='generate-sitemap', method='GET',
			    url=BLOG_ADMIN_RELATIVE_PATH + 'generate_sitemap?id=%d&cursor=%s' % (id + 1, next_cursor))
			self.write('站点地图生成任务添加成功')
		else:
			self.write('站点地图生成完毕')
			memcache.delete('get_sitemap')


class GenerateTagsPage(yui.RequestHandler):
	def get(self):
		generate_tags()
		self.write('标签生成任务添加成功')


class GenerateCategoriesPage(yui.RequestHandler):
	def get(self):
		generate_categories()
		self.write('分类生成任务添加成功')


class GenerateFeedPage(BaseHandler):
	def get(self):
		limit = 100
		query = Article.all().filter('published =', True)
		articles, cursor = get_fetch_result_with_valid_cursor(query_with_cursor(query, self.GET['cursor']), limit)
		if articles:
			last_updated = iso_time_format(articles[0].mod_time)
			content = self.render('feed.xml', {'articles': articles, 'last_updated': last_updated})
			Feed(content=content.decode('utf-8'), cursor=cursor).put()
			deferred.defer(ping_hubs, BLOG_FEED_URL)
			if len(articles) < limit:
				self.write('Feed已生成，没有更新的文章了，确认Google Reader已收录后，可切换回正常feed链接，并删除所有Feed实体')
			else:
				self.write('Feed已生成')
		else:
			self.write('没有更新的文章了，确认Google Reader已收录后，可切换回正常feed链接，并删除所有Feed实体')


class AddArticleByEmail(yui.RequestHandler):
	def post(self):
		mail_message = mail.InboundEmailMessage(self.request.body)
		reply_to = parseaddr(mail_message.sender)[1]
		title = decode_header(mail_message.subject)[0]
		title = title[0].decode(title[1] or 'utf-8').strip()
		if reply_to not in EMAIL_WRITERS:
			logging.warning(u'未授权用户<%s>尝试添加文章，您可在app.yaml里更改接收邮件地址以避免垃圾邮件' % reply_to)
			mail.send_mail(ADMIN_EMAIL, reply_to, u'Re: ' + title, u'文章添加失败，您不在邮件列表内')
			return
		if not title:
			mail.send_mail(ADMIN_EMAIL, reply_to, u'Re: ' + title, u'发表失败，标题为空')
			return

		format = 0
		content = ''
		msg = mail_message.original
		charsets = msg.get_charsets()
		for part, charset in izip(msg.walk(), charsets):
			content_type = part.get_content_type()
			if content_type == 'text/plain' and format == 0 and not content:
				payload = part.get_payload(decode=True)
				if payload:
					content = payload.decode(charset or 'utf-8', 'ignore').strip()
			elif content_type == 'text/html':
				payload = part.get_payload(decode=True)
				if payload:
					content = payload.decode(charset or 'utf-8', 'ignore').strip()
					if content:
						format = 2
						break

		if not content:
			mail.send_mail(ADMIN_EMAIL, reply_to, u'Re: ' + title, u'发表失败，内容为空')
		if REPLACE_SPECIAL_CHARACTERS_FOR_URL:
			url = formatted_date_for_url() + replace_special_characters_for_url(title)
		else:
			url = formatted_date_for_url() + title
		if Article.all().filter('url =', url).count(1):
			mail.send_mail(ADMIN_EMAIL, reply_to, u'Re: ' + title, u'发表失败，同链接的文章已存在')
			return

		try:
			article = Article(
				title=title,
				url=url,
				content=content,
				format=format,
				published=True
			)
			article.put()
			url = '%s%s%s' % (MAJOR_HOST_URL, BLOG_HOME_RELATIVE_PATH, article.quoted_url())
			mail.send_mail(ADMIN_EMAIL, reply_to, u'Re: ' + title, u'发表成功\n' + url, html=u'发表成功，查看<a href="%s">发表后的文章</a>' % url)
			clear_article_memcache()
			deferred.defer(ping_hubs, BLOG_FEED_URL)
			deferred.defer(ping_xml_rpc, MAJOR_HOST_URL + BLOG_HOME_RELATIVE_PATH + article.quoted_url())
		except:
			mail.send_mail(ADMIN_EMAIL, reply_to, u'Re: ' + title, u'发表失败，数据库出错或正忙')


class MaintainPage(BaseHandler):
	def get(self):
		self.echo('maintain.html', {
		    'title': '维护',
		    'page': 'maintain'
		})


class FlushCachePage(yui.RequestHandler):
	def get(self):
		yui.flush_all_server_cache()
		memcache.flush_all()
		self.write('缓存已清空')


class UpdateTagsCountPage(yui.RequestHandler):
	def get(self):
		update_tags_count()
		self.write('标签计数已更新')


class UpdateArticlesRepliesPage(yui.RequestHandler):
	def get(self):
		deferred.defer(update_articles_replies)
		self.write('文章评论数更新任务添加成功')


class CalendarTokenPage(BaseHandler):
	def get(self):
		import gdata.auth
		import gdata.calendar
		import gdata.calendar.service
		import gdata_for_gae

		context = {
		    'title': '短信提醒',
		    'page': 'calendar_token',
		    'msg': '',
		    'token': ''
		}
		if ADMIN_PASSWORD:
			context['use_pw'] = True
			calendar_client = gdata_for_gae.programmatic_login(ADMIN_EMAIL, ADMIN_PASSWORD)
			if calendar_client:
				context['msg'] = '当前使用账号密码方式登录，已通过认证'
			else:
				context['msg'] = '当前使用账号密码方式登录，但密码不正确'
		else:
			context['use_pw'] = False
			scope = 'http://www.google.com/calendar/feeds/'
			feed = self.GET['feed']
			if feed:
				auth_token = gdata.auth.extract_auth_sub_token_from_url(self.request.uri)
				if auth_token:
					try:
						calendar_client = gdata.calendar.service.CalendarService()
						gdata_for_gae.run_on_appengine(calendar_client, user=ADMIN_EMAIL, url=feed)
						calendar_client.UpgradeToSessionToken(auth_token)
						context['msg'] = 'Token保存成功'
						context['token'] = gdata_for_gae.load_auth_token(ADMIN_EMAIL)
					except:
						context['msg'] = 'Token验证失败'
				else:
					self.redirect(str(gdata.auth.generate_auth_sub_url(self.request.uri, (scope,))))
					return
			else:
				calendar_client = gdata.calendar.service.CalendarService()
				gdata_for_gae.run_on_appengine(calendar_client, user=ADMIN_EMAIL)
				if not isinstance(calendar_client.token_store.find_token(scope), gdata.auth.AuthSubToken):
					context['msg'] = '尚未保存有效Token'
				else:
					context['msg'] = '已存在有效Token'
					context['token'] = gdata_for_gae.load_auth_token(ADMIN_EMAIL)
		self.echo('calendar_token.html', context)

	def post(self):
		import gdata_for_gae
		gdata_for_gae.del_auth_token(ADMIN_EMAIL)
		self.write('Token已成功删除')


class SubscribePage(BaseHandler):
	def get(self):
		self.echo('subscribe.html', {
		    'title': 'PubSubHubbub订阅与退订',
		    'page': 'subscribe'
		})

	def post(self):
		feed = self.POST['feed']
		if not feed:
			self.write('请填写feed地址')
			return
		mode = self.POST['mode']
		if mode == 'ping':
			try:
				ping_hubs(feed)
				self.write('发布成功')
			except:
				self.write('发布失败，你可尝试重试')
		elif mode in ('subscribe', 'unsubscribe'):
			verify_token = `random()`
			memcache.set('hub_verify_token', verify_token)
			if 200 <= send_subscription_request('https://pubsubhubbub.appspot.com/subscribe', mode, verify_token, feed) <= 299:
				self.write('提交成功')
			else:
				self.write('请求发送失败，您可尝试重试')
		else:
			self.write('请求有误，不支持该请求方式')


class RemoveOldSubscribersPage(yui.RequestHandler):
	def get(self):
		old_subscribers = Subscriber.all(keys_only=True).filter('time <', datetime.utcnow() - timedelta(days=1)).fetch(1000)
		if old_subscribers:
			db.delete(old_subscribers)
			memcache.delete('get_subscribers')
		self.write('更新完毕')


class TwitterStatusPage(BaseHandler):
	def get(self):
		self.echo('twitter_status.html', {
			'title': 'Twitter状态',
			'page': 'twitter_status',
			'twitter': get_twitter() if TWITTER_CONSUMER_KEY and TWITTER_CONSUMER_SECRET else None
		})

	def post(self):
		if TWITTER_CONSUMER_KEY and TWITTER_CONSUMER_SECRET:
			content = self.request.POST['content']
			if content:
				content = content.strip()
			if content:
				if get_twitter():
					if post_tweet(content):
						self.write('发布成功。')
					else:
						self.write('发布失败，可能是Google App Engine或Twitter出现了问题，请稍后重试。')
				else:
					self.write('发布失败，您的博客尚未与Twitter账号进行关联。')
			else:
				self.write('发布失败，您未填写任何内容。')
		else:
			self.write('发布失败，您的博客尚未与Twitter账号进行关联。')


class TwitterOauthPage(BaseHandler):
	def get(self):
		if TWITTER_CONSUMER_KEY and TWITTER_CONSUMER_SECRET:
			success = True
			TWITTER_REQUEST_TOKEN_URL = 'https://api.twitter.com/oauth/request_token'
			params = get_oauth_params({}, TWITTER_REQUEST_TOKEN_URL)
			try:
				res = urlfetch.fetch(url=TWITTER_REQUEST_TOKEN_URL, headers={'Authorization': 'OAuth ' + dict2qs(params)}, method='POST')
				if res.status_code != 200:
					success = False
					logging.error('Fetch request token error.\nstatus_code: %s\nheaders: %s\nparams: %s' % (res.status_code, res.headers, params))
			except:
				success = False

			if success:
				content = qs2dict(res.content)
				if content['oauth_callback_confirmed'] != 'true':
					success = False
					logging.error('Fetch request token error.\nstatus_code: %s\nheaders: %s\nparams: %s' % (res.status_code, res.headers, params))
		else:
			success = False

		if success:
			memcache.set(content['oauth_token'], content['oauth_token_secret'], 600, namespace='TwitterRequestToken')
			self.redirect('https://api.twitter.com/oauth/authorize?oauth_token=%s' % content['oauth_token'])
		else:
			self.echo('twitter_oauth.html', {
				'title': '获取request token失败',
				'page': 'twitter_oauth'
			})


class TwitterCallbackPage(BaseHandler):
	def get(self):
		if TWITTER_CONSUMER_KEY and TWITTER_CONSUMER_SECRET:
			msg = ''
			GET = self.request.GET
			oauth_token = GET['oauth_token']
			if oauth_token:
				oauth_token_secret = memcache.get(oauth_token, 'TwitterRequestToken')
				if oauth_token_secret:
					TWITTER_ACCESS_TOKEN_URL = 'https://api.twitter.com/oauth/access_token'
					params = get_oauth_params({
						'oauth_token': oauth_token,
						'oauth_verifier': GET['oauth_verifier']
					}, TWITTER_ACCESS_TOKEN_URL, oauth_token_secret)

					try:
						res = urlfetch.fetch(url=TWITTER_ACCESS_TOKEN_URL, headers={'Authorization': 'OAuth ' + dict2qs(params)}, method='POST')
						if res.status_code != 200:
							logging.error('Exchanging access token error.\nstatus_code: %s\nheaders: %s\nparams: %s' % (res.status_code, res.headers, params))
							msg = '交换access token失败，可能是Google App Engine或Twitter出现了问题，请稍后重试。'
					except:
						msg = '交换access token失败，可能是Google App Engine或Twitter出现了问题，请稍后重试。'

					content = qs2dict(res.content)
					set_twitter(name=content['screen_name'], token=content['oauth_token'], secret=content['oauth_token_secret'])
				else:
					msg = '交换access token失败，可能是oauth_token无效或已过期，请重试。'
			else:
				logging.error('Missing or wrong oauth_token: ' + oauth_token)
				msg = '交换access token失败，缺少oauth_token，请重试。'
		else:
			msg = '您尚未设置Twitter应用的密钥，如需启用该功能，请参考<a href="status">Twitter状态</a>页面进行设置。'

		if msg:
			self.echo('twitter_callback.html', {
				'title': 'Twitter关联成功失败',
				'page': 'twitter_callback'
			})
		else:
			self.redirect('./status')
