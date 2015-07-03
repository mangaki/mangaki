var pieces;

function loadMenu() {
  pieces = new Bloodhound({
    datumTokenizer: function(d) { return d.tokens; },
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    prefetch: '/data/' + category + '.json',
    remote: '/data/' + category + '/%QUERY.json'
  });

  pieces.initialize();

  $('.typeahead').typeahead(null, {
    name: 'pieces',
    source: pieces.ttAdapter(),
    templates: {
      suggestion: Handlebars.compile([
        '<p class="repo-language">{{year}}</p>',
        '<p class="repo-name">{{value}}</p>',
        '<p class="repo-description">{{description}}</p>'
      ].join(''))
    }
  });
}

$(document).ready(function() {
  $('input.typeahead').on('typeahead:selected', function(event, selection) {
    location.href = '/' + category + '/' + selection.id;
    $(this).val('');
  }).on('typeahead:autocompleted', function(event, selection) {
    location.href = '/' + category + '/' + selection.id;
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
