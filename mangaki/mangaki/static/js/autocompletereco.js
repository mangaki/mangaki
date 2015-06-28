var pieces;

function loadMenureco() {
  pieces = new Bloodhound({
    datumTokenizer: function(d) { return d.tokens; },
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    // prefetch: '/recommend/' + work_id + '/' + target_id + '.json',
    remote: '/recommend/' + work_id + '/' + target_id + '/%QUERY.json'
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
    location.href = '/u/' + selection.username ;
    $(this).val('');
  }).on('typeahead:autocompleted', function(event, selection) {
    location.href = '/u/' + selection.username ;
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
    location.href = '/' + category + '/' + id;
  })
}

function deletePiece(piece) {
  $.post('/delete/', {id: $(piece.parentNode).data('id')}, function(category) {
    refresh(category)
  });
}
