// This contains the current loaded decks for each position.
var globalWorks = {
    dejaVu: []
};

function vote(elt) {
    entity = $(elt).closest('.data');
    work_id = entity.data('id');
    choice = $(elt).data('choice');
    pos = entity.data('pos');
    $.post('/work/' + work_id, {choice: choice}, function(rating) {
        if(rating === '') {
            // FIXME: We should take the vote into account after the
            // user signs up or logs in.
            var next = window.location.pathname +
                window.location.search + window.location.hash;
            window.location.assign(
                '/user/signup?next=' + encodeURIComponent(next));
        }
        if(typeof(sort_mode) !== 'undefined' && sort_mode === 'mosaic' && rating)
            loadCard(pos);
        else {
            if (rating === 'none')
                $(elt).siblings().filter('[data-choice!=' + rating + ']').removeClass('not-chosen');
            else if (rating) {
                $(elt).siblings().filter('[data-choice!=' + rating + ']').addClass('not-chosen');
                $(elt).removeClass('not-chosen');
            }
        }
    });
}

function suggestion(mangaki_class) {
    $.post('/' + mangaki_class + '/' + $('#id_work').val(), {
        'work': $('#id_work').val(),
        'problem': $('#id_problem').val(),
        'message': $('#id_message').val()
    }).success(function(data) {
        $('#alert').hide()
        if($('#success').css('display') === 'none')
            $('#success').show();
        $('#success').html('Merci d\'avoir contribué à Mangaki !');
        setTimeout(function() {
            $('#success').hide();
            $('#suggestionModal').modal('hide');
        }, 1000);
    }).error(function(data) {
        $('#success').hide();
        if($('#alert').css('display') === 'none')
            $('#alert').show();
        // for(line in data.responseJSON) {
        $('#alert').text(data.responseJSON['problem']);
        // }
    });
}

function displayWork(pos, work) {
    var display_votes = true;
    if(work === undefined) {
        work = {'id': 0, 'category': 'dummy', 'title': 'Chargement…', 'poster': '/static/img/chiro.gif', 'synopsis': ''}
        display_votes = false;
    } else {
        globalWorks.dejaVu.push(work.id);
    }
    var selector = ':nth-child(' + pos + ')';
    var work_div = $('.manga-sheet' + selector + ' .data');
    work_div.data('category', work['category']);
    work_div.data('id', work['id']);
    work_div.find('.work-snapshot-title h4').text(work['title']);
    work_div.find('.work-synopsis').text(work['synopsis']);
    $('[data-toggle="tooltip"]').tooltip('fixTitle');
    work_div.find('a.work-snapshot').attr('href', '/' + work_div.data('category') + '/' + work_div.data('id'));
    work_div.fadeOut().promise().done(function () {
            work_div.find('.work-votes').promise().done(function () {
                work_div.find('.work-votes').show();
                work_div.find('.work-snapshot-image img').attr('src', work['poster']);
                work_div.fadeIn();
        });
    });
    if(display_votes) {
        if(work['rating'] === 'willsee')
            work_div.find('.work-votes a[data-choice!=willsee]').addClass('not-chosen');
    } else
        work_div.find('.work-votes').fadeOut();
}

function actuallyLoadCard(pos) {
    var works = globalWorks[pos];

    var work = works.shift();
    if (!work)
        return loadCard(pos);

    while (globalWorks.dejaVu.indexOf(work.id) !== -1) {
        work = works.shift();
        if (!work)
            return loadCard(pos);
    }
    displayWork(pos, work);
}

function loadCard(pos) {
    displayWork(pos);
    if (globalWorks[pos])
        return actuallyLoadCard(pos);

    // TODO: abort in case there is no unseen card, to prevent infinite recursion.
    return $.getJSON('/data/card/' + category + '/' + pos + '.json', function(works) {
        globalWorks[pos] = works;
        return actuallyLoadCard(pos);
    });
}
