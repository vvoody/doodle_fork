$(function(){
	var $textarea = $('#content').markItUp(BbcodeSettings);
	$('.switcher li').click(function() {
		var $switcher = $(this);
		$textarea.markItUpRemove();
		var newSet = $switcher.attr('class');
		switch(newSet) {
			case 'bbcode':
				$textarea.markItUp(BbcodeSettings);
				break;
			case 'html':
				$textarea.markItUp(HtmlSettings);
		}
		return false;
	});
});