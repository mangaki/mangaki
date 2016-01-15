import _ from 'lodash'
import $ from 'jquery'
import { loadCard } from 'ui/work'

/** Initialize the vote system
 * If a sortMode is specified (sortMode !== null), then it means that the vote system will be able on a collection of works.
 * If there is no sortMode, then it means that the vote system will be able on a specific work.
 **/
export function initializeVoteSystem (sortMode = null) {
  function vote (elt) {
    const entity = $(elt).closest('.data')
    const choice = $(elt).data('choice')

    const workId = entity.data('id')
    const pos = entity.data('pos')

    $.post(`/work/${workId}`, {choice}, rating => {
      if (_.isEmpty(rating)) {
        window.location = '/user/signup'
      }

      if (sortMode && sortMode === 'mosaic' && rating) {
        loadCard(pos)
      } else {
        $(elt).siblings().filter(`[data-choice!=${rating}]`).addClass('not-chosen')
        if (rating === 'none') {
          $(elt).addClass('not-chosen')
        } else {
          $(elt).removeClass('not-chosen')
        }
      }
    })
  }

  $('.btn-vote').click(vote)
}

