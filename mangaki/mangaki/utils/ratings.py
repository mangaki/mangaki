from django.conf import settings


def pk_from_object_or_pk(obj):
    return getattr(obj, 'pk', obj)


def get_anonymous_ratings(session, works=None):
    """
    Compute the set of anonymous ratings currently stored in the session.

    Arguments:
        request -- The Request object we are currently handling.
        works   -- An iterable of Work instances or primary keys, or None.

    Returns:
        ratings -- A dictionary mapping Work primary keys to their rating
            string ('like', 'dislike', etc.)
    """
    ratings = session.get(settings.ANONYMOUS_RATINGS_SESSION_KEY, {})
    if works is not None:
        filtered_ratings = {}
        for work in works:
            # Accept Work models as well as primary key integers
            work = str(pk_from_object_or_pk(work))
            rating = ratings.get(work)
            if rating is not None:
                filtered_ratings[work] = rating
        ratings = filtered_ratings
    # Recall that keys in the session dictionary are always converted to
    # strings by serialization. We convert them back to integers.
    return {int(work_pk): choice for work_pk, choice in ratings.items()}


def clear_anonymous_ratings(session):
    """
    Removes any existing anonymous ratings.
    """
    del session[settings.ANONYMOUS_RATINGS_SESSION_KEY]


def current_user_ratings(request, works=None):
    """
    Compute the set of ratings for the current user.

    This handles both the case where the user is logged in and the case where
    it is an anonymous user, in which case the rating is fetched from the
    session.

    If the `works` argument is given, then only the ratings for the given works
    will be considered.

    Arguments:
        request -- The Request object we are currently handling.
        works   -- An iterable of Work instances or primary keys, or None.

    Returns:
        ratings -- A dictionary mapping Work primary keys to their rating
            string ('like', 'dislike', etc.)
    """
    user = request.user
    if user.is_anonymous:
        return get_anonymous_ratings(request.session, works)
    else:
        qs = user.rating_set.all()
        if works is not None:
            qs = qs.filter(work__in=works)
        return dict(qs.values_list('work_id', 'choice'))


def current_user_rating(request, work):
    """
    Get the rating the current user gave to a specific work.

    This handles both the case where the user is logged in and the case where
    it is an anonymous user, in which case the rating is fetched from the
    session.

    Note: If the ratings for several different works are needed, you should use
    the `current_user_ratings` function directly instead.

    Arguments:
        request -- The Request object we are currently handling.
        work    -- A Work object or primary key for which the rating is
            required.

    Returns:
        rating -- The rating that the current user gave to the work, or None if
            there is no such rating.
    """
    work = int(pk_from_object_or_pk(work))
    return current_user_ratings(request, [work]).get(work)


def current_user_set_toggle_rating(request, work, choice):
    """
    Update the rating the current user gave to a specific work.

    As this function's name indicated, if the user already rated the work with
    the same choice, this will undo (toggle) this rating instead of being a
    no-op. This corresponds to Mangaki's current UI where clicking again on an
    existing rating will un-rate the work.

    Arguments:
        request -- The Request object we are currently handling.
        work    -- The Work object (or its primary key) that we are currently
            rating.
        choice  -- The rating we want to assign (or remove) from the work.

    Returns:
        choice -- The new rating associated with the work for the current user.
            In case an existing rating was removed, this will be None instead.
    """
    user = request.user
    if user.is_authenticated:
        old_ratings = user.rating_set.filter(work=work, choice=choice)
        if old_ratings:
            return None
        else:
            user.rating_set.update_or_create(work=work, defaults={'choice': choice})
            return choice
    else:
        request.session.modified = True
        # Recall that keys in the session dictionary are always converted to
        # strings by serialization.
        work = str(pk_from_object_or_pk(work))
        ratings_dict = request.session.setdefault(
            settings.ANONYMOUS_RATINGS_SESSION_KEY, {})
        current_rating = ratings_dict.get(work)
        if current_rating == choice:
            del ratings_dict[work]
            return None
        else:
            ratings_dict[work] = choice
            return choice
