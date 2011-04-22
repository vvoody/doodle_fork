$(function() {
	var $load_button = $('p.wp-pagenavi>a');
	var loading = false;
	var $commentlist = $('#commentlist>ol');
	var $comment = $('#comment');
	var allow_comment = $('#commentform').length;
	var next_cursor = '';
	var is_admin = typeof(comment_delete_url) != 'undefined';
	var comment_fetch_url = home_path + 'comment/json/'+ article_id + '/';
	var $bbcode = $('#bbcode');

	function generate_comment(comment) {
		var html = [];
		html.push('<li class="comment"><div class="comment-info"><a id="comment-id-');
		html.push(comment.id);
		if (comment.url) {
			html.push('" href="');
			html.push(comment.url);
		}
		html.push('">');
		html.push(comment.user_name);
		html.push('</a> @');
		html.push(comment.time);
		if (is_admin) {
			html.push(' <a href="');
			html.push(comment_delete_url);
			html.push(comment.id);
			html.push('/">[删除]</a>');
		}
		html.push(' <a href="#respond" class="comment-reply-link">[回复]</a></div><div>');
		html.push(comment.content);
		html.push('</div></li>');
		return html.join("");
	}

	function bind_events_for_comment($html, id, user_name) {
		$html.find('a.comment-reply-link').click(function() {
			if (!allow_comment) {return;}
			var comment = [$comment.val()];
			comment.push('[url=#comment-id-');
			comment.push(id);
			comment.push(']@');
			comment.push(user_name);
			comment.push('[/url]: ');
			$comment.focus().val(comment.join(''));
			$bbcode.attr('checked', true);
			return false;
		});
	}

	$load_button.click(function(){
		if (loading) {
			return false;
		}
		loading = true;
		var url = comment_fetch_url;
		if (next_cursor) {
			url += next_cursor;
		}

		$.getJSON(url, function(json) {
			next_cursor = json.next_cursor;
			if (!next_cursor) {
				$('div.comments').remove();
			} else {
				$load_button.text('载入下10条评论');
			}
			var comments = json.comments;
			var length = comments.length;
			if (length) {
				for (var index = 0; index < length; ++index) {
					var comment = comments[index];
					bind_events_for_comment($(generate_comment(comment)).appendTo($commentlist), comment.id, comment.user_name);
				}
			}
			loading = false;
		});
		_gaq.push(['_trackEvent', 'Comment', 'Load', article_id]);
		return false;
	});
});