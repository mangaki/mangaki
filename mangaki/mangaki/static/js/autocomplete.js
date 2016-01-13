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

function loadMenuReco() {
  pieces = new Bloodhound({
    datumTokenizer: function(d) { return d.tokens; },
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    prefetch: '/getuser/' + work_id + '.json',
    remote: '/getuser/' + work_id + '/%QUERY.json'
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
    prefetch: '/getuser.json',
    remote: '/getuser/%QUERY.json'
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
    if (!selection.description) {
    	if (!selection.work_id)
        location.href = '/u/' + selection.username ;
      else {
        $.post('/recommend/'+ selection.work_id +'/'+ selection.id, function(status) {
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
    } else
      location.href = '/' + category + '/' + selection.id;
    $(this).val('');
  }).on('typeahead:autocompleted', function(event, selection) {
    if (!selection.description) {
     if (!selection.work_id) { location.href = '/u/' + selection.username ; }
     else {
      $.post('/recommend/'+ selection.work_id +'/'+ selection.id,  function(status) {
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
  } else { location.href = '/' + category + '/' + selection.id; }
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

function addPairing(artistID, workID) {
  $.post('/artist/' + artistID + '/add/' + workID, {artist_id: artistID, work_id: workID}, function(data) {
    $('.typeahead').attr('placeholder', 'Merci d\'avoir contribué à Mangaki !');
  });
}

function deletePiece(piece) {
  $.post('/delete/', {id: $(piece.parentNode).data('id')}, function(category) {
    refresh(category)
  });
}
