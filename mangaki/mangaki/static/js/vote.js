function vote(work_id, choice) {
    $.post('/work/' + work_id, {choice: choice}, function(rating) {
        if(rating) {
            $('#votes_' + work_id + ' a[data-choice!=' + rating + ']').addClass('not-chosen');
            $('#votes_' + work_id + ' a[data-choice=' + rating + ']').removeClass('not-chosen');
        }
    });
}
