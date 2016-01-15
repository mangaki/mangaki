import $ from 'jquery'
/** Mangaki initialization **/

/** Initialize the CSRF interceptor for jQuery AJAX calls **/
import 'utils/csrf.js'

$(document).ready(() => {
  const modules = [
    'skin' // Look'n'feel my Mangaki!
  ]

  modules.forEach(module => {
    require(`./${module}`)
  })
})
