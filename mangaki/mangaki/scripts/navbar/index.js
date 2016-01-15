import $ from 'jquery'

$(document).ready(() => {
  $('nav [href="{{ request.path }}"]').parents('li').addClass('active')
})
