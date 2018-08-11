from mangaki.models import ExternalRating, Rating

PRESETS = {
    'STRICT': {
        '10-10': 'favorite',
        '8-9': 'like',
        '5-7': 'neutral',
        '0-4': 'dislike'
    },
    'STANDARD': {
        '9-10': 'favorite',
        '6-8': 'like',
        '5-5': 'neutral',
        '0-4': 'dislike'
    },
    'GENTLE': {
        '8-10': 'favorite',
        '5-7': 'like',
        '0-4': 'dislike'
    }
}


def is_in_range(range_: str, value: float):
    low, high = list(map(int, range_.split('-')))
    return low <= value <= high


class RatingMappingRule:
    def __init__(self, mangaki_value):
        self.value = mangaki_value

    def can_apply(self, external_rating: ExternalRating):
        raise NotImplementedError

    @classmethod
    def from_range_of_values(cls, range_, rating_value):
        rule = cls(rating_value)
        rule.can_apply = lambda rating: is_in_range(range_, rating.value)
        return rule

    def apply(self, external_rating: ExternalRating):
        if self.can_apply(external_rating):
            return self.value


class RatingMappingPolicy:

    def __init__(self, rules):
        self.rules = rules

    def map(self, external_rating):
        for rule in self.rules:
            value = rule.apply(external_rating)
            if value:
                return Rating(
                    user=external_rating.user,
                    work=external_rating.work,
                    choice=value
                )


def build_policy_based_on_preset(preset):
    rules = [RatingMappingRule.from_range_of_values(range_, value) for range_, value in  preset.items()]
    return RatingMappingPolicy(rules)


StrictPolicy = build_policy_based_on_preset(PRESETS['STRICT'])
StandardPolicy = build_policy_based_on_preset(PRESETS['STANDARD'])
GentlePolicy = build_policy_based_on_preset(PRESETS['GENTLE'])

POLICIES = {
    'strict': StrictPolicy,
    'standard': StandardPolicy,
    'gentle': GentlePolicy
}
