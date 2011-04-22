$(function(){
	var submitting = false;
	var $info = $('.info');
	var $body = $('body');
	var $html = $('html');
	function show(text){
		$info.html(text).show();
		submitting = false;
		if ($body.scrollTop()) {
			$body.animate({scrollTop: 0}, 500);
		} else if ($html.scrollTop()) {
			$html.animate({scrollTop: 0}, 500);
		} // 剩下的情况是scrollTop为0，无需滚动
	}
	function ajax_get(url){
		$.ajax({
			'url': url,
			'type': 'GET',
			'error': function(){
				show('抱歉，遇到不明状况，发送失败了');
			},
			'success': show,
			'timeout': 100000
		});
	}
	$('#flush-cache').click(function(){
		if (!submitting) {
			submitting = true;
			ajax_get('/admin/flush_cache');
		}
	});
	$('#generate—sitemap').click(function(){
		if (!submitting) {
			submitting = true;
			ajax_get('/admin/generate_sitemap');
		}
	});
	$('#generate-categories').click(function(){
		if (!submitting) {
			submitting = true;
			ajax_get('/admin/generate_categories');
		}
	});
	$('#generate-tags').click(function(){
		if (!submitting) {
			submitting = true;
			ajax_get('/admin/generate_tags');
		}
	});
	$('#generate-feed').click(function(){
		if (!submitting) {
			submitting = true;
			ajax_get('/admin/generate_feed');
		}
	});
	$('#update—tags—count').click(function(){
		if (!submitting) {
			submitting = true;
			ajax_get('/admin/update_tags_count');
		}
	});
	$('#update-articles-replies').click(function(){
		if (!submitting) {
			submitting = true;
			ajax_get('/admin/update_articles_replies');
		}
	});
	$('#remove-old-subscribers').click(function(){
		if (!submitting) {
			submitting = true;
			ajax_get('/admin/remove_old_subscribers');
		}
	});
});