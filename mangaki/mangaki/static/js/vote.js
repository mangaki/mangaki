"use strict";

var globalWorks = {
    orphans: [],
    dejaVu: [],
};

function vote(elt) {
    var entity = $(elt).closest('.data');
    var work_id = entity.data('id');
    var choice = $(elt).data('choice');
    var pos = entity.data('pos');
    $.post('/vote/' + work_id, {choice: choice}, function(rating) {
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

function vote_dpp(elt) {
    var entity = $(elt).closest('.data');
    var work_id = entity.data('id');
    var choice = $(elt).data('choice');
    var pos = entity.data('pos');
    $.post('/dpp/' + work_id, {choice: choice}, function(rating) {
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
    work_div.data('category', work.category);
    work_div.data('id', work.id);
    work_div.find('.work-snapshot-title h4').text(work.title);
    work_div.find('.work-synopsis').text(work.synopsis);
    $('[data-toggle="tooltip"]').tooltip('fixTitle');
    work_div.find('a.work-snapshot').attr('href', '/' + work_div.data('category') + '/' + work_div.data('id'));
    work_div.fadeOut().promise().done(function () {
            work_div.find('.work-votes').promise().done(function () {
                if (display_votes)
                    work_div.find('.work-votes').show();
                work_div.find('.work-snapshot-image img').attr('src', work['poster']);
                work_div.fadeIn();
        });
    });
    if(display_votes) {
        if(work.rating === 'willsee')
            work_div.find('.work-votes a[data-choice!=willsee]').addClass('not-chosen');
    } else
        work_div.find('.work-votes').fadeOut();
}

function filterWorks(pos) {
    var dejaVu = globalWorks.dejaVu;
    return globalWorks[pos] = globalWorks[pos].filter(function (work) {
        return dejaVu.indexOf(work.id) === -1;
    });
}

function loadCardFrom(pos, works) {
    globalWorks.orphans = globalWorks.orphans.filter(function (pos) {
        return globalWorks[pos].length == 0;
    });
    displayWork(pos, works.shift());
    while (globalWorks.orphans.length && works.length)
        displayWork(globalWorks.orphans.shift(), works.shift());
}

function loadCard(pos) {
    displayWork(pos);
    if (globalWorks[pos]) {
        var works = filterWorks(pos);
        if (works.length)
            return loadCardFrom(pos, works);
    }

    return $.getJSON('/data/card/' + category + '/' + pos + '.json', function(works) {
        globalWorks[pos] = works;
        works = filterWorks(pos);

        if (works.length)
            return loadCardFrom(pos, works);

        // Let's try our best and use another position's cards
        for (var other = 1; other < 5; ++other) {
            if (!globalWorks[other])
                continue;

            var works = filterWorks(other);
            if (works.length)
                return loadCardFrom(pos, works);
        }

        // Oh man! We'll broadcast our poor situation
        if (globalWorks.orphans.indexOf(pos) !== -1)
            globalWorks.orphans.push(pos);
    });
}
