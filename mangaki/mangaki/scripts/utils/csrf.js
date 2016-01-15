import _ from 'lodash'
import $ from 'jquery'

// using jQuery
function getCookie (name) {
  if (!_.isEmpty(document.cookie)) {
    const cookies = document.cookie.split(';')
    for (let i = 0; i < cookies.length; i++) {
      const cookie = $.trim(cookies[i])
      // Does this cookie string begin with the name we want?
      if (_.startsWith(cookie, name)) {
        return decodeURIComponent(cookie.substring(name.length + 1))
      }
    }
  }
  return null
}
var csrftoken = getCookie('csrftoken')

function csrfSafeMethod (method) {
  // these HTTP methods do not require CSRF protection
  return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method))
}

$.ajaxSetup({
  beforeSend (xhr, settings) {
    if (!csrfSafeMethod(settings.type) && !this.crossDomain) {
      xhr.setRequestHeader('X-CSRFToken', csrftoken)
    }
  }
})
