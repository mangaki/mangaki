import $ from 'jquery'

function initializeSuggestionUI () {
  $('.btn-suggest').click(suggestion)
}

function suggestion (elt) {
  const workCategory = $(elt).data('category')
  const work = $('#id_work').val()
  const problem = $('#id_problem').val()
  const message = $('#id_message').val()
  $.post(`/${workCategory}/${work}`, {
    work,
    problem,
    message
  }).done(data => {
    $('#alert').hide()
    if ($('#success').css('display') === 'none') {
      $('#success').show()
    }

    $('#success').html(`Merci d'avoir contribué à Mangaki !`)
    setTimeout(() => {
      $('#success').hide()
      $('#suggestionModal').modal('hide')
    }, 1000)
  }).fail((xhr, textStatus, err) => {
    console.error('Failed to suggest to Mangaki', err)
    $('#success').hide()

    if ($('#alert').css('display') === 'none') {
      $('#alert').show()
    }

    if (textStatus) {
      $('#alert').text(`Une erreur est survenue, envoyez nous ce code: ${textStatus} !`)
    }
  })
}

initializeSuggestionUI()
