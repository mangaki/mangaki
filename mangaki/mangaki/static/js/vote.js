function vote(work_id, choice) {
    $.post('/work/' + work_id, {choice: choice}, function(rating) {
        if(rating) {
            $('#votes_' + work_id + ' > [data-choice!=' + rating + ']').addClass('not-chosen');
            $('#votes_' + work_id + ' > [data-choice=' + rating + ']').removeClass('not-chosen');
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
        if($('#success').css('display') == 'none')
            $('#success').show();
        $('#success').html('Merci d\'avoir contribué à Mangaki !');
        setTimeout(function() {
            $('#success').hide();
            $('#suggestionModal').modal('hide');
        }, 1000);
    }).error(function(data) {
        $('#success').hide();
        if($('#alert').css('display') == 'none')
            $('#alert').show();
        // for(line in data.responseJSON) {
        $('#alert').text(data.responseJSON['problem']);
        // }
    });
}
