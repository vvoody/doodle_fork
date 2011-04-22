# -*- coding: utf-8 -*-

from datetime import timedelta
from os import environ
import re
from urllib import quote


DOODLE_VERSION = '1.2' # 当前Doodle版本
CHECK_NEW_VERSION = True # 是否检测新版本

APPID = environ['APPLICATION_ID'] # 应用ID
# eg:
# APPID = environ['APPLICATION_ID']
# APPID = 'abcdegf'
BLOG_TITLE = u'' # 博客标题
BLOG_SUB_TITLE = u''# 博客副标题
BLOG_DESCRIPTION = BLOG_SUB_TITLE # 用于FEED的博客描述
BLOG_AUTHOR = '' # 博客作者
MAJOR_DOMAIN = environ['HTTP_HOST'] # 主要域名，不想生成*.appspot.com形式的域名的话，可以设为自己的域名（必须是Google Apps域名）
# eg:
# MAJOR_DOMAIN = environ['HTTP_HOST']
# MAJOR_DOMAIN = 'abcdegf.appspot.com'
# MAJOR_DOMAIN = 'www.abcdegf.com'
ONLY_USE_MAJOR_DOMAIN = False # 是否只用主要域名，为真时，所有非该域名的http链接都会被重定向到主要域名
FEED_DOMAIN = '' # 供稿所用域名，如果不想用子目录的话，可以设置为子域名
MAJOR_HOST_URL = 'http://' + MAJOR_DOMAIN
if FEED_DOMAIN:
	BLOG_FEED_URL = 'http://%s/' % FEED_DOMAIN # 博客供稿地址
	BLOG_COMMENT_FEED_URL = 'http://%s/comment' % FEED_DOMAIN # 博客评论供稿地址
else:
	BLOG_FEED_URL = MAJOR_HOST_URL + '/feed'
	BLOG_COMMENT_FEED_URL = MAJOR_HOST_URL + '/comment-feed'
QUOTED_BLOG_FEED_URL = quote(BLOG_FEED_URL, '')
BLOG_HOME_RELATIVE_PATH = '/' # 博客首页相对路径，可以改为'/blog/'等子目录
BLOG_WAP_RELATIVE_PATH = BLOG_HOME_RELATIVE_PATH + 'wap/' # 博客WAP页相对路径
BLOG_ADMIN_RELATIVE_PATH = BLOG_HOME_RELATIVE_PATH + 'admin/' # 博客管理相对路径
# 若修改了以上的路径，还需修改yaml文件和\static\markitup\sets\bbcode\set.js的previewParserPath

SOCIAL_MEDIAS = [
	{'icon': 'atom', 'url': '/comment-feed', 'title': '订阅博客评论', 'text': 'Comments Feed', 'rel': 'nofollow'}
] # 社交媒体链接

NAV_LINKS = [
	{'url': '/', 'text': '首页', 'level': 1},
	{'url': BLOG_WAP_RELATIVE_PATH, 'text': '手机浏览', 'level': 1},
	{'url': 'javascript:void(0)', 'text': '订阅', 'level': 1},
	{'url': 'https://www.google.com/reader/view/feed/' + QUOTED_BLOG_FEED_URL, 'text': '订阅到Google Reader', 'level': 2},
	{'url': 'http://mail.qq.com/cgi-bin/feed?u=' + BLOG_FEED_URL, 'text': '订阅到QQ邮箱', 'level': 2},
	{'url': 'http://reader.youdao.com/b.do?url=' + QUOTED_BLOG_FEED_URL, 'text': '订阅到有道', 'level': 2},
	{'url': 'http://www.zhuaxia.com/add_channel.php?url=' + QUOTED_BLOG_FEED_URL, 'text': '订阅到抓虾', 'level': 2},
	{'url': 'http://xianguo.com/subscribe?url=' + QUOTED_BLOG_FEED_URL, 'text': '订阅到鲜果', 'level': 2},
] # 导航栏链接，为了避免多次转义，如果网址包含中文或特殊字符，请在这里写百分号转义过的网址

LINKS = [
	{'url': 'http://code.google.com/appengine/', 'text': 'Google App Engine', 'rel': 'nofollow'},
] # 友情链接，为了避免多次转义，如果网址包含中文或特殊字符，请在这里写百分号转义过的网址

GOOGLE_ANALYTICS_ID = '' # Google Analytics web property ID，没有就留空
GOOGLE_CSE_ID = '' # Google自定义搜索引擎ID，没有就留空，你可以在这里获取：http://www.google.com/cse/manage/create

DISPLAY_PERFORMANCE_TO_EVERYONE = False # 是否在页面底部向所有人显示响应时间等信息，为False则只向管理员显示。注意开启会影响ETag的有效性，使客户端缓存失效

ADMIN_EMAIL = '' # 管理员邮箱，收发邮件时需要用到
EMAIL_WRITERS = [ADMIN_EMAIL] # 允许用于添加新文章的邮件列表
APP_SENDER = u'%s <no-reply@%s.appspotmail.com>' % (BLOG_TITLE, APPID) # 对外发送邮件采用的邮箱
MAX_SEND_TO = 5 # 每篇评论最多允许通知多少个人，0为禁用通知功能。如果未开启收费，请注意每分钟不能发送超过8封email。
SEND_LEVEL = 1 | 2 # 什么等级的用户才能发送提醒邮件，可用值见model.py中的USER_FLAGS
NOTIFY_WHEN_REPLY = True # 在收到新评论时，是否向管理员发送邮件和短信通知
SEND_INTERVAL = 600 # 最短的发送间隔（单位为秒，下同），0表示不检测发送间隔。在此时间内连续收到多篇评论将只会发出一次通知。
ADMIN_PASSWORD = '' # 管理员密码，用于访问Google日历来发送短信，为空时使用AuthSub方式登录。如果觉得设置Google日历的token很麻烦，可以直接在这里填写Google账号的密码。注意：不推荐这样使用，因为存在密码泄露的风险，需要妥善保管好您的setting文件。
NOTIFY_FEED_URL = 'http://www.google.com/calendar/feeds/default/private/full' # 用于提醒的Google日历的feed地址，仅当使用密码登录时有效。

LANGUAGE = 'zh-CN' # 博客文章采用的主要语言

THEMES = ['koi', 'iphonsta', 'freshpress'] # 主题

LOCAL_TIME_ZONE = '' # pytz中定义的时区名，为空时则按LOCAL_TIME_DELTA进行处理。注意：pytz可以正确处理夏时令，但性能较慢。如果不需要该功能，可以把pytz文件夹删除，节省上传时间。
LOCAL_TIME_DELTA = timedelta(hours=8) # 本地时区偏差
DATE_FORMAT = '%Y-%m-%d' # 日期格式
SECONDE_FORMAT = '%Y-%m-%d %H:%M:%S' # 时间格式（精确到秒）
MINUTE_FORMAT = '%Y-%m-%d %H:%M' # 时间格式（精确到分）

ARTICLES_PER_PAGE = 10 # 每页文章数
COMMENTS_PER_PAGE = 10 # 每页评论数
RELATIVE_ARTICLES = 5 # 相关文章数
LATEST_COMMENTS_FOR_SIDEBAR = 5 # 侧边栏显示的最新评论数
LATEST_COMMENTS_LENGTH = 20 # 侧边栏显示的最新评论截取的长度
LATEST_COMMENTS_FOR_FEED = 10 # 评论FEED显示的最新评论数
RECENT_TWEETS = 5 # 侧边栏显示的最新Tweets

ARTICLES_CACHE_TIME = 600 # 每页文章缓存时间，0表示永久缓存（不推荐），下同。
ARTICLE_CACHE_TIME = 600 # 单篇文章缓存时间
FEED_CACHE_TIME = 3600 # FEED缓存时间
SITEMAP_CACHE_TIME = 3600 # 网站地图缓存时间
COMMENTS_CACHE_TIME = 600 # 每页评论缓存时间
CATEGORY_CACHE_TIME = 600 # 分类缓存时间
TAGS_CACHE_TIME = 600 # 标签缓存时间
SIDEBAR_BAR_CACHE_TIME = 600 # 侧边栏缓存时间
USER_CACHE_TIME = 600 # 当前用户缓存时间
SUBSCRIBER_CACHE_TIME = 21600 # 单个FEED订阅数缓存时间
SUBSCRIBERS_CACHE_TIME = 86400 # FEED订阅总数缓存时间

COUNTER_TASK_DELAY = 60 # 计数任务延迟执行时间

CATEGORY_PATH_DELIMETER = ',' # 分类路径的分隔符，确保你的分类名中不会出现这个字符。一旦定义好了，请不要随意更改。由于URL中“/”为分隔符，建议不要在分类名、标签名和文章名中出现这个字符，其他符号也最好不要用。

SUMMARY_DELIMETER = re.compile(r'\r?\n\r?\n\[cut1\]\r?\n') # 分隔摘要和文章内容的标记，分隔符之前的作成摘要，分隔符前后的都作为文章内容
SUMMARY_DELIMETER2 = re.compile(r'\r?\n\r?\n\[cut2\]\r?\n') # 分隔摘要和文章内容的标记，分隔符之前的作成摘要，之后的为文章内容
# 一篇文章中同时出现2种分隔符时，以第一种优先；同时出现多次分隔符时，以最先出现的优先。

OUTPUT_FULLTEXT_FOR_FEED = True # 是否全文输出ATOM
HUBS = ['http://pubsubhubbub.appspot.com/'] # 所用的PubSubHubbub服务器，不需要可设为空列表，详情请参考：http://code.google.com/p/pubsubhubbub/wiki/Hubs
XML_RPC_ENDPOINTS = ['http://blogsearch.google.com/ping/RPC2', 'http://rpc.pingomatic.com/', 'http://ping.baidu.com/ping/RPC2'] # XML-RPC端口，不需要可设为空列表

ENABLE_TAG_CLOUD = True # 是否开启标签云，对于低配置的机器，标签云可能会占用较多CPU。
REPLACE_SPECIAL_CHARACTERS_FOR_URL = False # 在自动生成URL时，是否将空格、引号、尖括号、&、#、%替换成“-”，在写英文标题时可能会需要
if REPLACE_SPECIAL_CHARACTERS_FOR_URL:
	URL_SPECIAL_CHARACTERS = re.compile(r'[\s\"\'&#<>%]+')
	URL_REPLACE_CHARACTER = '-'

ONLINE_VISITORS_EXPIRY_TIME = 600 # 在线人数过期时间，小于等于0则不统计在线人数（可略微加快响应速度）

# 下面的设置用于与Twitter关联，相关方法请查看博客管理的Twitter页面
TWITTER_CONSUMER_KEY = '5ucqWXMUcaCN5RtQzjweyA' # Twitter consumer key
TWITTER_CONSUMER_SECRET = 'eot8U4N8YR0o6i4qG1ztkBRhkzrxOh2CoFPnYXh7I08' # Twitter consumer secret
GOO_GL_API_KEY = 'AIzaSyCxYwlXA7T3NXJQI3a1BGtVdx3uaKGQvpY' # Google URL Shortener API key，用于在发Tweet时生成短网址，可以在这里获取：http://code.google.com/apis/console/
