(function(){
	var $scroller;
	var $body = $('body');
	var $html = $('html');
	if ($body.scrollTop()) {
		$scroller = $body;
	} else if ($html.scrollTop()) {
		$scroller = $html;
	} else {
		$body.scrollTop(1); // 一些浏览器的body元素不支持scrollTop()，因此调用它来判断
		if ($body.scrollTop()) {
			$scroller = $body.scrollTop(0);
		} else {
			$scroller = $html;
		}
	}
	function scrollTo(top) {
		$scroller.animate({scrollTop: top < 0 ? 0 : top}, 1000);
	}
	$body.delegate('a[href^=#]', 'click', function(ev){ // 只捕捉URL以#开头的A元素的click事件
		var href = $(this).attr('href');
		if (href == '#') {
			scrollTo(0);
			ev.preventDefault();
		}
		var $href = $(href);
		if ($href.length) {
			scrollTo($href.offset().top);
			ev.preventDefault();
		}
	});
})();