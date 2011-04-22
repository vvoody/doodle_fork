# -*- coding: utf-8 -*-

from google.appengine.ext.webapp import util
import yui

import admin_view
from setting import BLOG_ADMIN_RELATIVE_PATH

application = yui.WsgiApplication([
	(BLOG_ADMIN_RELATIVE_PATH + 'article_counter/', admin_view.ArticleCounterTaskPage, yui.Response),
	(BLOG_ADMIN_RELATIVE_PATH, admin_view.AdminPage),
	(BLOG_ADMIN_RELATIVE_PATH + 'article/unpublished/(.*)', admin_view.UnpublishedArticlesPage),
	(BLOG_ADMIN_RELATIVE_PATH + 'article/edit/(.+)', admin_view.EditArticlePage, yui.Response),
	(BLOG_ADMIN_RELATIVE_PATH + 'article/new/', admin_view.AddArticlePage),
	(BLOG_ADMIN_RELATIVE_PATH + 'article/delete/(.+)', admin_view.DeleteArticlePage),
	(BLOG_ADMIN_RELATIVE_PATH + 'category/new/', admin_view.AddCategoryPage),
	(BLOG_ADMIN_RELATIVE_PATH + 'category/delete/', admin_view.RemoveCategoryPage),
	(BLOG_ADMIN_RELATIVE_PATH + 'category/move/', admin_view.MoveArticlesBetweenCategoriesPage),
	(BLOG_ADMIN_RELATIVE_PATH + 'tag/new/', admin_view.AddTagPage),
	(BLOG_ADMIN_RELATIVE_PATH + 'tag/delete/', admin_view.RemoveTagPage),
	(BLOG_ADMIN_RELATIVE_PATH + 'tag/move/', admin_view.MoveArticlesBetweenTagsPage),
	(BLOG_ADMIN_RELATIVE_PATH + 'comment/edit/(\d+)/(\d+)/', admin_view.EditCommentPage, yui.Response),
	(BLOG_ADMIN_RELATIVE_PATH + 'comment/delete/(\d+)/(\d+)/', admin_view.DeleteCommentPage),
	(BLOG_ADMIN_RELATIVE_PATH + 'user/search/', admin_view.SearchUserPage),
	(BLOG_ADMIN_RELATIVE_PATH + 'user/edit/', admin_view.EditUserPage),
	(BLOG_ADMIN_RELATIVE_PATH + 'user/edit/(\d+)/(\d+)/', admin_view.EditUserByCommentPage),
	(BLOG_ADMIN_RELATIVE_PATH + 'maintain', admin_view.MaintainPage),
	(BLOG_ADMIN_RELATIVE_PATH + 'generate_sitemap', admin_view.GenerateSitemapPage, yui.Response),
	(BLOG_ADMIN_RELATIVE_PATH + 'generate_tags', admin_view.GenerateTagsPage, yui.Response),
	(BLOG_ADMIN_RELATIVE_PATH + 'generate_categories', admin_view.GenerateCategoriesPage, yui.Response),
	(BLOG_ADMIN_RELATIVE_PATH + 'generate_feed', admin_view.GenerateFeedPage, yui.Response),
	(BLOG_ADMIN_RELATIVE_PATH + 'flush_cache', admin_view.FlushCachePage, yui.Response),
	(BLOG_ADMIN_RELATIVE_PATH + 'update_tags_count', admin_view.UpdateTagsCountPage, yui.Response),
	(BLOG_ADMIN_RELATIVE_PATH + 'update_articles_replies', admin_view.UpdateArticlesRepliesPage, yui.Response),
	(BLOG_ADMIN_RELATIVE_PATH + 'calendar_token', admin_view.CalendarTokenPage),
	(BLOG_ADMIN_RELATIVE_PATH + 'subscribe', admin_view.SubscribePage),
	(BLOG_ADMIN_RELATIVE_PATH + 'remove_old_subscribers', admin_view.RemoveOldSubscribersPage),
	(BLOG_ADMIN_RELATIVE_PATH + 'twitter/status', admin_view.TwitterStatusPage),
	(BLOG_ADMIN_RELATIVE_PATH + 'twitter/oauth', admin_view.TwitterOauthPage),
	(BLOG_ADMIN_RELATIVE_PATH + 'twitter/callback', admin_view.TwitterCallbackPage),
	(r'/_ah/mail/.+', admin_view.AddArticleByEmail)
], quote_path=False)

def main():
	util.run_wsgi_app(application)


if __name__ == '__main__':
	main()
