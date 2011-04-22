# -*- coding: utf-8 -*-

import logging
from time import time

from google.appengine.ext.webapp import util
import yui

import view
import hook
from setting import BLOG_HOME_RELATIVE_PATH, BLOG_WAP_RELATIVE_PATH, MAJOR_DOMAIN, ONLY_USE_MAJOR_DOMAIN, FEED_DOMAIN


application = yui.WsgiApplication([
	(BLOG_HOME_RELATIVE_PATH, view.HomePage),
	(BLOG_HOME_RELATIVE_PATH + r'(\d{4}/\d{2}/\d{2}/.+)', view.ArticlePage),
	(BLOG_HOME_RELATIVE_PATH + r'comment/json/(\d+)/(.*)', view.CommentJson),
	(BLOG_HOME_RELATIVE_PATH + r'comment/(\d+)/(.*)', view.CommentPage),
	(BLOG_HOME_RELATIVE_PATH + r'relative/(\d+)', view.RelativeArticlesJson),
	(BLOG_HOME_RELATIVE_PATH + r'point/(\d+)/(\d)', view.PointPage, yui.Response),
	(BLOG_HOME_RELATIVE_PATH + 'preview/', view.PreviewPage, yui.Response),
	(BLOG_HOME_RELATIVE_PATH + 'tag/(.+)', view.TagPage),
	(BLOG_HOME_RELATIVE_PATH + 'category/(.+)', view.CategoryPage),
	(BLOG_HOME_RELATIVE_PATH + 'search', view.SearchPage),
	(BLOG_HOME_RELATIVE_PATH + 'feed', view.FeedPage),
#	(BLOG_HOME_RELATIVE_PATH + 'feed', view.GeneratedFeedPage, yui.Response),
	(BLOG_HOME_RELATIVE_PATH + 'comment-feed', view.CommentFeedPage),
	(BLOG_HOME_RELATIVE_PATH + r'sitemap\.xml', view.SitemapPage, yui.Response),
	(BLOG_HOME_RELATIVE_PATH + 'profile/', view.ProfilePage),
	(BLOG_WAP_RELATIVE_PATH, view.WapHomePage),
	(BLOG_WAP_RELATIVE_PATH + r'(\d{4}/\d{2}/\d{2}/.+)', view.WapArticlePage),
	(BLOG_WAP_RELATIVE_PATH + r'comment/(\d+)/(.*)', view.WapCommentPage),
	(BLOG_WAP_RELATIVE_PATH + '.*', view.NotFoundMobilePage),
	(r'/robots\.txt', view.RobotsPage),
	(BLOG_HOME_RELATIVE_PATH + r'article/(\d+)', view.RedirectToArticlePage, yui.Response),
	# 如果是从Discuz!转向Doodle，可以开启下列重定向
#	(r'/bbs/viewthread\.php', view.RedirectToArticlePage, yui.Response),
#	(r'/bbs/thread-(\d+)-\d+-\d+\.html', view.RedirectToArticlePage, yui.Response),
#	(r'/bbs/archiver/tid-(\d+)(?:-page-\d+)?\.html', view.RedirectToArticlePage, yui.Response),
#	(r'/bbs/archiver/', view.RedirectToHomeOrArticlePage, yui.Response),
#	(r'/bbs/rss\.php', view.RedirectToFeedPage, yui.Response),
#	('/bbs/wap/?', view.RedirectToWapHomePage, yui.Response),
#	('/bbs', view.RedirectToHomePage, yui.Response),
#	('/bbs/.*', view.RedirectToHomePage, yui.Response),
	('/login|/logout', view.LoginoutPage, yui.Response),
	('/_ah/warmup', view.WarmupPage, yui.Response),
	(BLOG_HOME_RELATIVE_PATH + 'hub/callback', view.VerifySubscription, yui.Response),
	('.*', view.NotFoundPage)
]
#, yui.Response
, quote_path=False
)

if ONLY_USE_MAJOR_DOMAIN:
	application = yui.redirect_to_major_domain(application, MAJOR_DOMAIN)

if FEED_DOMAIN:
	feed_application = yui.WsgiApplication([('/', view.FeedPage, yui.Response), ('/comment', view.CommentFeedPage)])
	application = yui.multi_domain_mapping((FEED_DOMAIN, feed_application), ('*', application))

def main():
	hook.db_count = 0
	hook.db_time = 0
	hook.db_start_time = 0
	hook.request_arrive_time = time()

	util.run_wsgi_app(application)

if __name__ == '__main__':
	main()
