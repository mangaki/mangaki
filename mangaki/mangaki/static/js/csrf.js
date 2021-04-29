// SPDX-FileCopyrightText: 2014, Mangaki Authors
// SPDX-License-Identifier: AGPL-3.0-only
// using jQuery
function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
var csrftoken = getCookie('csrftoken');

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}
$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken);
        }
    }
});

function betterFetch(url, params) {
  if (csrfSafeMethod(params.method || 'GET')) {
    return fetch(url, params);
  } else {
    const userHeaders = params.headers || {};
    delete params.headers;
    return fetch(url, Object.assign({}, {
      headers: Object.assign({}, {
        'X-CSRFToken': csrftoken
      }, userHeaders)
    }, params));
  }
}
