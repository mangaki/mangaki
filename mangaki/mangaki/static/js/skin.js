$(document).ready(function() {
	$('.work-votes .btn').hover(function(){
		$(this).stop(true, false).animate({ width: "150%" }, 200);
	}, function() {
		$(this).stop(true, false).animate({ width: "100%" }, 200);
	});
});
