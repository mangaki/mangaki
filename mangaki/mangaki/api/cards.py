import enum

from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from mangaki.models import Category, Work
from mangaki.utils.ratings import current_user_ratings

NB_POINTS_DPP = 10
POSTERS_PER_PAGE = 24


class SlotCardTypes(enum.Enum):
    popularity = 'popular'
    controversy = 'controversial'
    top = 'top'
    random = 'random'
    dpp = 'dpp'


slots_choices = [
    (item.name, item)
    for item in SlotCardTypes
]

slot_dispatchers = {
    SlotCardTypes.popularity: lambda qs: qs.popular(),
    SlotCardTypes.controversy: lambda qs: qs.controversial(),
    SlotCardTypes.top: lambda qs: qs.top(),
    SlotCardTypes.random: lambda qs: qs.random().order_by('?'),
    SlotCardTypes.dpp: lambda qs: qs.dpp(NB_POINTS_DPP)
}


class CardSlotRateThrottle(UserRateThrottle):
    scope = 'mosaic_slot_card'


class CardSlotQuerySerializer(serializers.Serializer):
    category = serializers.CharField(max_length=300, required=True)
    slot_type = serializers.ChoiceField(required=True,
                                        choices=slots_choices)

    def validate_category(self, category: str) -> str:
        """Check that the category exists in the database.

        Args:
            category (string): A slug representing a Category object.

        Returns:
            The value of `category` unmodified.

        Raises
            :class:`serializers.ValidationError`: When the category does not exist.

        """

        if not Category.objects.filter(slug=category).exists():
            raise serializers.ValidationError('Category {} does not exists.'
                                              .format(category))

        return category


class CardSlotSerializer(serializers.ModelSerializer):
    category = serializers.CharField(source='category.slug')
    poster = serializers.SerializerMethodField()

    def get_poster(self, work: Work):
        return work.safe_poster(self.context['request'].user)

    class Meta:
        model = Work
        fields = ('id',
                  'category',
                  'title',
                  'poster',
                  'synopsis',
                  'nsfw')


@api_view(['GET'])
@permission_classes((AllowAny,))
@throttle_classes([CardSlotRateThrottle])
def get_card(request: Request, category: str, slot_sort_type: str):
    """
    Fetch the work card from the `category` using the `slot_sort_type` as "sorting" method.
    """

    card_slot_query_serializer = CardSlotQuerySerializer(data={
        'category': category,
        'slot_type': slot_sort_type
    })

    if not card_slot_query_serializer.is_valid():
        return Response(
            card_slot_query_serializer.errors,
            status=400
        )

    card_slot_query = card_slot_query_serializer.data
    queryset = (
        Category.objects.get(slug=card_slot_query['category'])
            .work_set.all()
    )

    rated_works = current_user_ratings(request)
    slot_type_chosen = SlotCardTypes[card_slot_query['slot_type']]
    queryset = (
        slot_dispatchers[slot_type_chosen](queryset)
            .exclude(id__in=list(rated_works))
    )

    works = queryset[:POSTERS_PER_PAGE]

    return Response(
        CardSlotSerializer(works, many=True,
                           context={'request': request}).data
    )
