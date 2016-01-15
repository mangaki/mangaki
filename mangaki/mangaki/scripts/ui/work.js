import $ from 'jquery'
import state from 'init/state'
import categories from 'constants/Categories'
import ratings from 'constants/Ratings'

const globalWorks = {
  dejaVu: []
}

export function displayWork (pos, work) {
  let showVotes = true
  if (!work) {
    work = {
      'id': 0,
      'category': categories.DUMMY,
      'title': 'Chargement',
      'poster': '/static/img/chiro.gif',
      'synopsis': ''
    }
    showVotes = false
  } else {
    globalWorks.dejaVu.push(work.id)
  }

  const selector = `:nth-child(${pos})`
  const workDiv = $(`.manga-sheet ${selector} .data`)
  workDiv.data('category', work.category)
  workDiv.data('id', work.id)

  const workNode = workDiv.find('h4 a')
  workNode.text(work.title)
  workNode.attr('title', work.synopsis)
  $('[data-toggle="tooltip"]').tooltip('fixTitle')
  workNode.attr('href', `/${work.category}/${work.id}`)

  workDiv.find('.manga-snapshot-image').hide().css('background-image', `url(${work.poster})`).fadeIn()

  if (showVotes) {
    workDiv.find('.manga-votes').fadeIn()
    if (work.rating === ratings.WILL_SEE) {
      workDiv.find(`.manga-votes a[data-choice!==${ratings.WILL_SEE}`).addClass('not-chosen')
    }
  } else {
    workDiv.find('.manga-votes').fadeOut()
  }
}

function showUnseenCard (pos) {
  const availableWorks = globalWorks[pos]

  let work = availableWorks.shift()
  if (!work) {
    return loadCard(pos)
  }

  /** As long as this work is already seen **/
  while (globalWorks.dejaVu.indexOf(work.id) !== -1) {
    work = availableWorks.shift()
    if (!work) {
      return loadCard(pos)
    }
  }

  displayWork(pos, work)
  return Promise.resolve(work)
}

export function loadCard (pos) {
  const {category} = state
  displayWork(pos)

  return new Promise((resolve, reject) => {
    setImmediate(() => {
      if (globalWorks[pos]) {
        showUnseenCard(pos).then(resolve, reject)
      }

      $.getJSON(`/data/card/${category}/${pos}.json`)
      .done(works => {
        globalWorks[pos] = works
        showUnseenCard(pos).then(resolve, reject)
      })
      .fail(err => {
        reject(err)
      })
    })
  })
}

export function loadReco (category, editor) {
  return new Promise((resolve, reject) => {
    $.getJSON(`/data/reco/{{ category }}/{{ editor }}.json`)
    .done(data => {
      try {
        data.forEach((work, pos) => {
          displayWork(pos + 1, work)
        })
        resolve()
      } catch (exc) {
        reject(exc)
      }
    })
    .fail((xhr, textStatus, err) => reject(err))
  })
}

