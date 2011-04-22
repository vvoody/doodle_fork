设置说明：

1. app.yaml：将YOUR_APPID改成你自己的应用ID。如果不用根目录，请更改admin.py和blog.py对应的链接。
2. cron.yaml：如果不用根目录，请更改相应的链接。
3. setting.py：都有说明，就不重复了。最主要的是BLOG_TITLE、BLOG_SUB_TITLE、BLOG_AUTHOR和MAJOR_DOMAIN。如果不用根目录，请更改BLOG_HOME_RELATIVE_PATH。
4. default_error.html、over_quota.html、timeout.html：将YOUR_BLOG_TITLE改成你的博客标题，YOUR_BLOG_SUB_TITLE改成博客副标题。如果不用根目录，请更改各个链接的地址。如有需要，也可根据自己的主题来更改样式。
5. static\favicon.ico：更改成你自己的图标。
6. static\theme和template：将自己的主题文件放在里面，并更改setting.py中关于主题的设定。
7. static\markitup\sets\bbcode\set.js：如果不用根目录，请更改previewParserPath。
8. static\theme\freshpress\js\maintain.js：如果不用根目录，请更改admin路径。


升级说明：

如果你没有自行修改过Doodle的源码：
1. 下载新版本。
2. 重新按照配置说明进行配置。（大部分设定可以参照以前的代码。）
3. 部署新版本。（建议备份老版本，以便出错时可以恢复。）
4. 如果有某个版本特定的升级说明，请按该说明进行操作。

如果你需要进行一些自定义的增强：
1. 建议你使用Mercurial来获取更新，并与你的改动进行merge；否则你需要每次手动查找和修改被改动的部分。这里有篇文章可以帮助你快速上手Mercurial：http://www.keakon.net/article/1865
2. 特别注意setting.py的更改。
3. 部署新版本。
4. 如果有某个版本特定的升级说明，请按该说明进行操作。


导入导出数据：

那些bulkloader开头的文件是用于导入导出数据的。
目前只支持导入Discuz!和WordPress的XML数据，某些地方需要自行处理，特别是自定义的字段。
数据可以在phpMyAdmin执行bulkloader_discuz.sql和bulkloader_wordpress.sql里的查询，将结果导出为XML格式，放在dontupload文件夹里，然后用bulkloader_discuz.bat和bulkloader_wordpress.bat上传。注意修改上传的URL参数，如有必要，还需要修改bulkloader_discuz.yaml和bulkloader_wordpress.yaml的配置（特别是xpath_to_nodes参数）。
其余的也可以自行研究数据库结构，构造一个bulkloader.yaml和转换函数。


用电子邮件发表日志：

用管理员账号发送邮件到“write@你的应用id.appspotmail.com”。
其中“write”可自行定义，修改app.yaml的“/_ah/mail/write@.+\.appspotmail\.com”，将“write”改成其他字符串即可。
邮件标题会作为日志标题，邮件内容作为日志内容。内容格式可为HTML或纯文本。


主题制作说明：

如果懂PHP和Python的基础语法的话，应该很容易就能从WordPress的主题移植过来。
不明白的地方可以参考已有主题的实现，模板文件在template文件夹下，静态文件在static\theme文件夹下。
如果要借用已有的JavaScript特效，最好能保持DOM结构一致，否则你需要对JavaScript进行一些修改。

Doodle中采用的是pyTenjin模板引擎，语法和Python差不多：
1. 语句由<?py ?>组成，一句一行，并从行首开始。
2. 语句缩进时要用tab，结束缩进时要用#关闭。
3. #{}表示当成字符串输出，${}表示当成字符串并进行HTML实体转义输出，其中可以调用Python函数。
4. <?PY ?>里是预编译的语句，这些语句只会被执行一次，里面的变量和函数不能被<?py ?>、#{}和${}所用，也不能使用<?py ?>和模板参数中的变量和函数。
5. #{{}}和${{}}用法和#{}、${}类似，但只能使用<?PY ?>中的变量和函数。
6. 子模板可以用include()函数载入。
7. for _ in cache_as和#endfor可以缓存模板的一部分，注意使用合理的参数。
8. 如果模板文件以<?py ?>语句结尾而导致出错，可以在后面加个空行。

注意：这次更新升级了pyTenjin的版本，如果你使用了自制的主题，请注意查阅变动。例如tenjin.helpers.html需要改为tenjin.html。