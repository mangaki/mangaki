// SPDX-FileCopyrightText: 2014, Mangaki Authors
// SPDX-License-Identifier: AGPL-3.0-only

$(document).ready(function() {
	$('.work-votes .btn').hover(function(){
		$(this).stop(true, false).animate({ width: "150%" }, 200);
	}, function() {
		$(this).stop(true, false).animate({ width: "100%" }, 200);
	});
});
