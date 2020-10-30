from collections import Counter, defaultdict
from typing import Tuple, List, Any, Dict, Optional

from django.contrib.auth.models import User

from mangaki.models import Rating, Work, Category, Recommendation
from mangaki.utils.fit_algo import get_algo_backup
from mangaki.utils.ratings import get_anonymous_ratings
from mangaki.utils.recommendations import get_personalized_ranking

SEE_CHOICES = {
    'seen': ('favorite', 'like', 'dislike', 'neutral'),
    'unseen': ('willsee',),
    'willsee': ('willsee',),
    'wontsee': ('wontsee',)
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
        works_per_pk = Work.objects.select_related('category').in_bulk(anon_ratings.keys())
        for pk, choice in anon_ratings.items():
            rating = Rating()
            rating.work = works_per_pk[pk]
            rating.choice = choice

            seen_work = rating.choice not in SEE_CHOICES['unseen']
            count_key = 'seen_{}' if seen_work else 'unseen_{}'
            counts[count_key.format(rating.work.category.slug)] += 1

            if already_seen == seen_work and rating.work.category.slug == category:
                ratings.append(rating)
    elif can_see:
        ratings = list(
            Rating.objects
            .filter(user=user,
                    work__category__slug=category,
                    choice__in=SEE_CHOICES['seen'] if already_seen else SEE_CHOICES['unseen'])
            .select_related('work', 'work__category')
        )

        categories = Category.objects.all()
        for category in categories:
            qs = Rating.objects.filter(user=user,
                                       work__category=category)

            seen = qs.filter(choice__in=SEE_CHOICES['seen']).count()
            unseen = qs.count() - seen

            counts['seen_{}'.format(category.slug)] = seen
            counts['unseen_{}'.format(category.slug)] = unseen
    else:
        ratings = []

    return ratings, counts


def build_profile_compare_function(algo_name: Optional[str],
                                   ratings: List[Rating],
                                   user: User):
    ordering = ['favorite', 'willsee', 'like', 'neutral', 'dislike', 'wontsee']

    # By default, sort by rating then name
    def default_compare_function(item):
        return ordering.index(item.choice), item.work.title.lower()

    if algo_name is not None:
        try:
            work_ids = [rating.work_id for rating in ratings]
            algo = get_algo_backup(algo_name)
            best_pos = get_personalized_ranking(algo, user.id, work_ids)
            ranking = defaultdict(lambda: len(ratings))
            for rank, pos in enumerate(best_pos):
                ranking[ratings[pos].id] = rank

            def special_compare_function(item):
                return ordering.index(item.choice), ranking[item.id]

            return special_compare_function
        except Exception as e:  # Two possible reasons: no backup or user not in backup
            pass

    return default_compare_function


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
