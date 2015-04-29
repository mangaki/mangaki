function getSheet(elt) {
    if($(elt).closest('.row').data('category') != 'dummy')
        location.href = '/' + $(elt).closest('.row').data('category') + '/' + $(elt).closest('.row').data('id');
}

function vote(elt) {
    work_id = $(elt).closest('.row').data('id');
    choice = $(elt).data('choice');
    $.post('/work/' + work_id, {choice: choice}, function(rating) {
        $(elt).siblings().filter('[data-choice!=' + rating + ']').addClass('not-chosen');
        if(rating)
            $(elt).removeClass('not-chosen');
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
