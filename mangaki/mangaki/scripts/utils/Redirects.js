import $ from 'jquery'
import categories from 'constants/Categories'

export function redirectToWorkDetailPage (elt) {
  const entity = $(elt).closest('.data')
  if (entity.data('category') !== categories.DUMMY) {
    location.href = `/${entity.data('category')}/${entity.data('id')}`
  }
}
