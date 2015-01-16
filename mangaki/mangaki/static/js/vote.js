function vote(work_id, choice) {
    $.post('/work/' + work_id, {choice: choice}, function(rating) {
        if(rating) {
            console.log('hiya')
            $('#votes_' + work_id + ' > [data-choice!=' + rating + ']').addClass('not-chosen');
            $('#votes_' + work_id + ' > [data-choice=' + rating + ']').removeClass('not-chosen');
        }
    });
}
