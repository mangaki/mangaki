// SPDX-FileCopyrightText: 2014, Mangaki Authors
// SPDX-License-Identifier: AGPL-3.0-only

var pieces;

function loadMenureco() {
  pieces = new Bloodhound({
    datumTokenizer: function(d) { return d.tokens; },
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    // prefetch: '/recommend/' + work_id + '/' + target_id + '.json',
    remote: Urls['reco-work'](work_id, target_id).replace('.json','/%QUERY.json')
  });

  pieces.initialize();

  $('.typeahead').typeahead(null, {
    name: 'pieces',
    source: pieces.ttAdapter(),
    templates: {
      suggestion: Handlebars.compile([
        '<p class="repo-name">{{ username }}</p>',
      ].join(''))
    }
  });
}

$(document).ready(function() {
  $('input.typeahead').on('typeahead:selected', function(event, selection) {
    location.href = Urls['profile'](selection.username) ;
    $(this).val('');
  }).on('typeahead:autocompleted', function(event, selection) {
    location.href = Urls['profile'](selection.username) ;
    $(this).val('');
  }).on('change', function(object, datum) {
    pieces.clearPrefetchCache();
     // lookup($(this).val());
     // $(this).val('');
  });
})

function lookup(query, category) {
  $.post('/lookup/', {query: query}, function(id) {
    // console.log(pieces);
    pieces.clearPrefetchCache();
    promise = pieces.initialize(true);
    promise.done(function() {console.log('win')}).fail(function() {console.log('fail')});
    // vote({id: id});
    location.href = Urls['work-detail'](category, id);
  })
}

function deletePiece(piece) {
  $.post('/delete/', {id: $(piece.parentNode).data('id')}, function(category) {
    refresh(category)
  });
}
