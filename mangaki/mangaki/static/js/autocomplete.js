// SPDX-FileCopyrightText: 2014, Mangaki Authors
// SPDX-License-Identifier: AGPL-3.0-only

var pieces;

function loadMenu() {
  pieces = new Bloodhound({
    datumTokenizer: function(d) { return Bloodhound.tokenizers.whitespace(d.title); },
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    remote: Urls['get-work'](category) + '?q=%QUERY'
  });

  pieces.initialize();

  $('.typeahead').typeahead(null, {
    name: 'pieces',
    source: pieces.ttAdapter(),
    templates: {
      suggestion: Handlebars.compile([
        '<p class="repo-language">{{year}}</p>',
        '<p class="repo-name">{{title}}</p>',
        '<p class="repo-description">{{synopsis}}</p>'
      ].join(''))
    }
  });
}

function loadMenuReco() {
  pieces = new Bloodhound({
    datumTokenizer: function(d) { return d.tokens; },
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    prefetch: Urls['get-user-for-reco'](work_id),
    remote: Urls['get-user-for-reco'](work_id).replace('.json','/%QUERY.json')
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

function loadMenuUser() {
  pieces = new Bloodhound({
    datumTokenizer: function(d) { return d.tokens; },
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    prefetch: Urls['get-user'](),
    remote: Urls['get-user']().replace('.json','/%QUERY.json')
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
  function handleRequest(event, selection) {
    if (!selection.synopsis) {
    	if (!selection.work_id) {
        location.href = Urls['profile'](selection.username) ;
      } else {
        $.post(Urls['reco-work'](selection.work_id, selection.id), function(status) {
          if (status === 'success') {
            $('#alert-reco').hide();
            if($('#success-reco').css('display') === 'none')
              $('#success-reco').show();
          }
          else {
            $('#success-reco').hide();
            if($('#alert-reco').css('display') === 'none')
              $('#alert-reco').show();
            if (category === 'anime')
              $('#alert-reco').html('Cet utilisateur a déjà vu l\'anime que vous voulez lui recommander');
            else
              $('#alert-reco').html('Cet utilisateur a déjà lu le manga que vous voulez lui recommander');
            if (status === 'nonsense')
              $('#alert-reco').html('Vous ne pouvez pas vous adresser vos propres recommandations!');
            if (status === 'double')
              $('#alert-reco').html('Vous avez déjà effectué cette recommandation');
          }
        });
      }
    }
    else if(typeof(artistID) !== 'undefined') {
      addPairing(artistID, selection.id);
    } else {
      location.href = Urls['work-detail'](category, selection.id);
    }
    $(this).val('');
  }
  $('input.typeahead').on('typeahead:selected', handleRequest)
                      .on('typeahead:autocompleted', handleRequest)
                      .on('change', function(object, datum) {
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

function addPairing(artistID, workID) {
  $.post(Urls['add-pairing'](artistID, workID), {artist_id: artistID, work_id: workID}, function(data) {
    $('.typeahead').attr('placeholder', 'Merci d\'avoir contribué à Mangaki !');
  });
}

function deletePiece(piece) {
  $.post('/delete/', {id: $(piece.parentNode).data('id')}, function(category) {
    refresh(category)
  });
}
