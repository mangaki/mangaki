import $ from 'jquery'
import './skin.scss'

$('.mangas-list .manga-sheet .btn').hover(function () {
  $(this).stop(true, false).animate({ width: '150%' }, 200)
}, function () {
  $(this).stop(true, false).animate({ width: '100%' }, 200)
})
