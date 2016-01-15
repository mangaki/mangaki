import state from 'init/state'
import { redirectToWorkDetailPage } from 'utils/Redirects'
import { loadCard, loadReco } from './work'
import $ from 'jquery'

function initializeRecoList () {
  loadReco(state.category, state.editor)
}

function initializeWorkList () {
  if (state.sortMode === 'mosaic') {
    for (let pos = 1; pos <= 4; pos++) {
      loadCard(pos)
    }
  }
}

function initializeWorkUI (view) {
  const views = {
    'reco-list': initializeRecoList,
    'work-list': initializeWorkList
  }

  try {
    views[view]()
  } catch (exc) {
    console.error(`Work UI initialization for view: ${view} failed!`, exc)
  }
}

export default function initializeUI () {
  $('.manga-snapshot-image').click(redirectToWorkDetailPage)
  $('.anime-snapshot-image').click(redirectToWorkDetailPage)

  initializeWorkUI(state.view)
}
