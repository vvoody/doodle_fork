$(function() {
	var $document = $(document);
	var $window = $(window);
	var complete = false;
	var loading = true;
	var $commentlist = $('#commentlist>ol'); // 评论列表
	var $comment = $('#comment'); // 编辑器的textarea元素
	var $temp = $('<ol/>'); // 用于临时存放新生成的评论
	var $comment_float_list = $('<ol class="commentlist comment-float-list"/>').appendTo(document.body).hide(); // 用于临时存放浮动的引用评论
	var $commentform = $('#commentform');
	var allow_comment = $commentform.length; // 若编辑器不存在，则说明不允许评论
	var next_cursor = '';
	var voting = false;
	var comment_order = true;
	var $comment_order_asc = $('#comment-order-asc');
	var $comment_order_desc = $('#comment-order-desc');
	var is_admin = typeof(comment_delete_url) != 'undefined'; // 只有管理员的页面才会定义comment_delete_url
	var $del_comment_button = $('<span id="del-comment-button">确认删除</span>');
	var comment_fetch_url = home_path + 'comment/json/'+ article_id + '/';

	function generate_comment(comment) {
		var html = [];
		html.push('<li><p class="comment-author"><img src="');
		html.push(comment.img);
		html.push('?s=48&amp;d=monsterid" class="avatar" height="48" width="48"/><cite><a id="comment-id-');
		html.push(comment.id);
		if (comment.url) { // 显示用户网址
			html.push('" href="');
			html.push(comment.url);
		}
		html.push('">');
		html.push(comment.user_name);
		html.push('</a></cite>');
		var uas = comment.ua;
		if (uas) { // 显示用户代理信息
			html.push('<span class="ua">');
			for (var i = 0, ua; i < uas.length; ++ i) {
				ua = comment.ua[i];
				html.push('<img src="/img/ua/');
				html.push(ua.replace(/ /g, '-'));
				html.push('.png" alt="');
				html.push(ua);
				html.push('" title="');
				html.push(ua);
				html.push('"/>');
			}
			html.push('</span>');
		}
		html.push('<br/><small><strong>');
		html.push(comment.time);
		html.push('</strong>');
		if (is_admin) { // 为管理员显示管理链接
			html.push(' <span class="edit-user"><a href="');
			html.push(user_edit_url);
			html.push(comment.id);
			html.push('/">[用户设定]</a></span> <span class="edit-comment"><a href="');
			html.push(comment_edit_url);
			html.push(comment.id);
			html.push('/">[编辑]</a></span> <span class="del-comment">[删除]</span>');
		}
		html.push('</small></p><div class="commententry" id="commententry-');
		html.push(comment.id);
		html.push('"><div>');
		html.push(comment.content);
		html.push('</div></div><p class="reply"><a class="comment-reply-link" href="#respond">回复</a></p></li>');
		return html.join("");
	}

	function bind_events_for_comment($html, id, user_name) {
		$html.find('a.comment-reply-link').click(function() { // 点击回复按钮
			reply(id, user_name);
		});
		$html.find('a[href^="#comment-id-"]').hover(function(ev) { // URL以 #comment-id- 开头的A元素
			var comment_author_id = $(this).attr('href').substr(12); // 评论id在12位以后
			var ref_comment_link = $commentlist.find('#comment-id-' + comment_author_id); // 被引用的评论
			if (ref_comment_link.length) {
				$comment_float_list.css({
					'top': ev.pageY,
					'left': ev.pageX + 50
				}).append(ref_comment_link.parent().parent().parent().clone().find('p.reply').remove().end()).fadeTo(1000, 0.9);
				// 显示浮动评论
				// ref_comment_link.parent().parent().parent()是被引用评论所在的li元素
				// 如果你的主题更改了DOM结构，这里可以改为查询父元素，直到找到li元素
				// 即ref_comment_link.parentsUntil('li').last().parent()
			}
		}, function() {
			$comment_float_list.hide().empty(); // 隐藏浮动评论
		});
		$html.find('pre>code').each(function(i, e) {hljs.highlightBlock(e, '    ')}); // 对评论进行代码高亮
		if (is_admin) { // 如果是管理员，在删除按钮后面显示确认删除按钮
			$html.find('span.del-comment').data('id', id).hover(function(){
				$(this).append($del_comment_button);
			}, function(){
				$del_comment_button.detach();
			});
		}
	}

	function get_comment() {
		var url = comment_fetch_url;
		if (next_cursor) {
			url += next_cursor;
		}
		if (!comment_order) { // 排序方式
			url += '?order=desc'
		}

		$.getJSON(url, function(json) {
			next_cursor = json.next_cursor;
			if (!next_cursor) {
				complete = true;
			}
			var comments = json.comments;
			var length = comments.length;
			if (length) {
				for (var index = 0; index < length; ++index) {
					var comment = comments[index];
					var $html = $(generate_comment(comment)).appendTo($temp);
					bind_events_for_comment($html, comment.id, comment.user_name);
				}
				$temp.children().unwrap().hide().appendTo($commentlist).slideDown(1000);

			}
			loading = false;
		});
		_gaq.push(['_trackEvent', 'Comment', 'Load', article_id]);
	}

	get_comment();

	(function () { // 获取相关文章
		$.getJSON(home_path + 'relative/' + article_id, function(json) {
			var length = json ? json.length : 0;
			if (length) {
				var html = ['<ul>'];
				for (var index = 0; index < length; ++index) {
					var article = json[index];
					html.push('<li><a href="');
					html.push(home_path);
					html.push(article.url);
					html.push('">');
					html.push(article.title);
					html.push('</a></li>');
				}
				html.push('</ul>');
				$('#relative-articles').append(html.join('')).slideDown(1000, function(){
					$(this).find('ul').animate({'left': '+2em'}, 1000);
				});
			}
		});
		_gaq.push(['_trackEvent', 'RelativeArticles', 'Load', article_id]);
	})();

	function reply(comment_id, comment_user) {
		if (!allow_comment) {return;}
		var comment = [$comment.val()];
		comment.push('[url=#comment-id-');
		comment.push(comment_id);
		comment.push(']@');
		comment.push(comment_user);
		comment.push('[/url]: ');
		setTimeout(function(){$comment.focus().val(comment.join(''));}, 100); // 在textarea里添加被回复人和评论id
	}

	$('pre>code').each(function(i, e) {hljs.highlightBlock(e, '    ')}); // 对文章进行代码高亮

	if ($comment.length) {
		$comment.markItUp(BbcodeSettings);
		var submitting = false;
		var $bbcode = $commentform.find('#bbcode');
		$commentform.submit(function() {
			if (submitting) return false;
			submitting = true;
			var val = $.trim($comment.val());
			if (!val) {
				msgbbox('拜托，你也写点内容再发表吧');
				submitting = false;
				return false;
			}
			var data = {'comment': val};
			if ($bbcode.attr('checked')) { // 检查是否启用BBCode
				data['bbcode'] = 'on';
			}
			$.ajax({
				'url': $commentform.attr('action'),
				'data': data,
				'dataType': 'json',
				'type': 'POST',
				'error': function(){
					submitting = false;
					msgbbox('抱歉，遇到不明状况，发送失败了');
				},
				'success': function(json){
					if (json.status == 200) {
						var comment = json.comment;
						var $html = $(generate_comment(comment));
						bind_events_for_comment($html, comment.id, comment.user_name);
						$html.hide().appendTo($commentlist).slideDown(1000); // 附加新评论
						$comment.val(''); // 清空textarea
						msgbbox('感谢您的回复，由于缓存原因，其他用户可能要几分钟后才能看到您的评论');
					} else {
						msgbbox(json.content);
					}
					submitting = false;
				},
				'timeout': 100000
			});
			_gaq.push(['_trackEvent', 'Comment', 'Reply', article_id]);
			return false;
		});
	}

	$('a.up, a.down').click(function (){ // 评分
		if (voting)
			return false;
		voting = true;
		var $this = $(this);
		var url = $this.attr('href');
		if (!url) {
			$this.unbind('click');
			voting = false;
			return false;
		}
		$.getJSON(url, function (json) {
			if (json.success) { // 评分后取消绑定，不允许再次评分
				$('a.up').text(json.like).removeAttr('href').unbind('click');
				$('a.down').text(json.hate).removeAttr('href').unbind('click');
			}
			voting = false;
		});
		_gaq.push(['_trackEvent', 'Point', 'Vote', article_id, $this.attr('class') == 'up' ? 1: 0]);
		return false;
	});

	if (allow_comment) {
		$('#comments').find('a').click(function() {$comment.focus();}); // 定位到textarea
	}

	$comment_order_asc.click(function() { // 评论顺序排列
		$comment_order_asc.addClass('selected');
		$comment_order_desc.removeClass('selected');
		if (comment_order) {
			return;
		}
		loading = true;
		$commentlist.empty();
		comment_order = true;
		complete = false;
		next_cursor = '';
		get_comment();
	});

	$comment_order_desc.click(function() { // 评论倒序排列
		$comment_order_desc.addClass('selected');
		$comment_order_asc.removeClass('selected');
		if (!comment_order) {
			return;
		}
		loading = true;
		$commentlist.empty();
		comment_order = false;
		complete = false;
		next_cursor = '';
		get_comment();
	});


	if (is_admin) {
		$del_comment_button.click(function() { // 点击确认删除按钮
			var $parent = $del_comment_button.parent();
			var $comment_li = $parent.parent().parent().parent();
			$.ajax({
				'url': comment_delete_url + $parent.data('id') + '/',
				'dataType': 'json',
				'type': 'POST',
				'error': function(){
					msgbbox('遇到不明状况，评论删除失败了');
				},
				'success': function(json){
					if (json.status == 204) {
						$comment_li.slideUp('2000', function(){
							$del_comment_button.detach(); // 移除确认删除按钮，但不移除click事件
							$comment_li.remove(); // 移除评论
						});
					} else {
						msgbbox(json.content);
					}
				},
				'timeout': 100000
			});
		});
	}

	$window.scroll(function(){ // 滚动到页底自动载入评论
		if (!complete && !loading && ($document.height() - $window.scrollTop() - $window.height() < 100)) {
			loading = true;
			get_comment();
		}
	});
});