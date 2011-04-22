$(function() {
	var $document = $(document);
	var $window = $(window);
	var $content = $('#content');
	var $loading = $('<div/>'); // 用于临时存放新载入的文章
	var loading = false;
	var $next_url = $('#content>.post-nav>.previous>a');
	var complete = false;
	var next_url = '';

	function set_next_url() {
		if ($next_url.length) {
			complete = false;
			next_url = $next_url.attr('href');
		} else {
			complete = true;
			next_url = '';
		}
	}
	set_next_url();

	function load() {
		$loading.load(next_url + ' #content', function() {
			$next_url = $loading.find('.post-nav>.previous>a');
			set_next_url();
			$('#content>.post-nav').remove(); // 删除当前页的下一页链接
			$loading.children().remove().children().hide().appendTo($content).slideDown(1000);
			loading = false;
		});
		_gaq.push(['_trackEvent', 'Page', 'Load', next_url]);
	}

	$window.scroll(function(){ // 滚动到页底自动载入更多文章
		if (!complete && !loading && ($document.height() - $window.scrollTop() - $window.height() < 100)) {
			loading = true;
			load();
		}
	});
});