$(function(){
	var submitting = false;
	var $body = $('body');
	var $html = $('html');
	var $form = $('form');
	var $info = $('.info');
	function show(text){
		$info.html(text).show();
		submitting = false;
		if ($body.scrollTop()) {
			$body.animate({scrollTop: 0}, 500);
		} else if ($html.scrollTop()) {
			$html.animate({scrollTop: 0}, 500);
		}
	}
	var param = {
		'type': $form.attr('method'),
		'error': function(){
			show('抱歉，遇到不明状况，发送失败了');
		},
		'success': show,
		'timeout': 100000
	};
	var url = $form.attr('action');
	if (url) {
		param['url'] = url;
	}
	$form.submit(function(){
		if (!submitting) {
			submitting = true;
			param['data'] = $form.serialize();
			$.ajax(param);
		}
		return false;
	});
	$(document).keydown(function(e){
		if (e.ctrlKey && e.which == 83) {
			$form.submit();
			return false;
		}
	});
});