# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

from collections import Counter, defaultdict
from typing import Tuple, List, Any, Dict, Optional

from django.contrib.auth.models import User
from django.utils import timezone
import pandas as pd

from mangaki.models import Rating, Work, Category, Recommendation
from mangaki.utils.fit_algo import get_algo_backup
from mangaki.utils.ratings import get_anonymous_ratings
from mangaki.utils.recommendations import get_personalized_ranking

seen_status = {
    'favorite': 'seen',
    'like': 'seen',
    'dislike': 'seen',
    'neutral': 'seen',
    'willsee': 'unseen',
    'wontsee': 'unseen'
}


def get_profile_ratings(request,
                        category: str,
                        already_seen: bool,
                        can_see: bool,
                        is_anonymous: bool,
                        user: User) -> Tuple[List[Rating], Counter]:
    counts = Counter()
    if is_anonymous:
        ratings = []
        anon_ratings = get_anonymous_ratings(request.session)
        ratings_df = pd.DataFrame(anon_ratings.items(), columns=('work_id', 'choice'))
        works_df = Work.objects.select_related('category').query(
            work__in=anon_ratings.keys()).values_list('work_id', 'title', 'category__slug')
        ratings_df = ratings_df.merge(works_df, on='work_id')
    elif can_see:  # Current user is allowed to access those ratings
        ratings_df = pd.DataFrame(
            Rating.objects
                .filter(user=user)
                .select_related('work', 'work__category')
                .values_list('work_id', 'choice', 'work__title', 'work__category__slug'),
            columns=('work_id', 'choice', 'work__title', 'work__category__slug')
        ).rename(columns={'work__title': 'title', 'work__category__slug': 'category__slug'})
    else:
        return pd.DataFrame(), {}

    ratings_df['seen'] = ratings_df['choice'].map(seen_status)
    ratings_df['rating_category'] = ratings_df.apply(
        lambda row: f"{row['seen']}_{row['category__slug']}", axis=1)
    counts = ratings_df['rating_category'].value_counts().to_dict()
    seen_value = 'seen' if already_seen else 'unseen'
    return ratings_df, ratings_df.query("category__slug == @category and seen == @seen_value"), counts


def get_work_rating_list(algo_name: Optional[str],
                         displayed_ratings_df: pd.DataFrame,
                         all_ratings_df: pd.DataFrame) -> List:

    ordering = dict(zip(['favorite', 'willsee', 'like', 'neutral', 'dislike', 'wontsee'], list('012345')))
    displayed_ratings_df['order'] = displayed_ratings_df['choice'].map(ordering)
    works = Work.objects.in_bulk(displayed_ratings_df['work_id'].tolist())

    if algo_name is None:  # Default sorting
        ordered_ratings = displayed_ratings_df.sort_values(['order', 'title'],
            key=lambda x: x.str.lower())
    else:
        algo = get_algo_backup(algo_name)
        # Limit display to available works in the algorithm
        available_works = set(algo.dataset.encode_work.keys())
        displayed_ratings_df = displayed_ratings_df.query('work_id in @available_works')
        work_ids_to_rank = displayed_ratings_df['work_id'].tolist()
        ranking = get_personalized_ranking(algo, all_ratings_df, work_ids_to_rank)
        displayed_ratings_df.index = range(len(work_ids_to_rank))
        ordered_ratings = displayed_ratings_df.iloc[ranking]

    work_rating_list = []
    for _, rating in ordered_ratings.iterrows():
        work = works[rating['work_id']]
        work.rating = rating['choice']
        work_rating_list.append({'work': work})

    return work_rating_list


ProfileRecoList = List[Dict[str, Any]]


def get_profile_recommendations(is_anonymous: bool,
                                can_see: bool,
                                user: User) -> Tuple[ProfileRecoList, ProfileRecoList]:
    received_recommendation_list = []
    sent_recommendation_list = []
    if not is_anonymous and can_see:
        received_recommendations = Recommendation.objects.filter(target_user=user).select_related('work',
                                                                                                  'work__category')
        sent_recommendations = Recommendation.objects.filter(user=user).select_related('work',
                                                                                       'work__category')
        for reco in received_recommendations:
            if Rating.objects.filter(work=reco.work, user=user,
                                     choice__in=['favorite', 'like', 'neutral', 'dislike']).count() == 0:
                received_recommendation_list.append(
                    {'category': reco.work.category.slug, 'id': reco.work.id, 'title': reco.work.title,
                     'username': reco.user.username})
        for reco in sent_recommendations:
            if Rating.objects.filter(work=reco.work, user=reco.target_user,
                                     choice__in=['favorite', 'like', 'neutral', 'dislike']).count() == 0:
                sent_recommendation_list.append(
                    {'category': reco.work.category.slug, 'id': reco.work.id, 'title': reco.work.title,
                     'username': reco.target_user.username})

    return received_recommendation_list, sent_recommendation_list
