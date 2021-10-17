# SPDX-FileCopyrightText: 2014, Mangaki Authors
# SPDX-License-Identifier: AGPL-3.0-only

from django import forms
from django.utils.translation import ugettext_lazy as _
from mangaki.models import Suggestion, Rating, Profile
from mangaki.utils.ratings import get_anonymous_ratings, clear_anonymous_ratings
from mangaki.choices import SUGGESTION_PROBLEM_CHOICES


class SuggestionForm(forms.ModelForm):
    class Meta:
        model = Suggestion
        fields = ['work', 'problem', 'message']
        widgets = {'work': forms.HiddenInput()}

    def __init__(self, *args, **kwargs):
        work = kwargs.pop('work', None)
        super(SuggestionForm, self).__init__(*args, **kwargs)

        # Remove redundant choices for NSFW works (e.g. don't display "Is NSFW" choice if work is NSFW)
        if work is not None:
            nsfw_state = 'nsfw' if work.nsfw else 'n_nsfw'
            new_choices = filter(lambda x: x[0] != nsfw_state, SUGGESTION_PROBLEM_CHOICES)
            self.fields['problem'].choices = new_choices


class SignupForm(forms.Form):
    import_ratings = forms.BooleanField(required=False, initial=True, label=_("Import my ratings"))
    newsletter_ok = forms.BooleanField(required=False, initial=False, label=_("Subscribe to Mangaki newsletter"))
    research_ok = forms.BooleanField(required=False, initial=False,
                                     label=_("My data can be released anonymously for research"))

    def signup(self, request, user):
        if self.cleaned_data['import_ratings']:
            ratings = get_anonymous_ratings(request.session)
            clear_anonymous_ratings(request.session)
            Rating.objects.bulk_create([
                Rating(user=user, work_id=work_id, choice=choice)
                for work_id, choice in ratings.items()
            ])

        Profile.objects.filter(id=user.profile.pk).update(
            newsletter_ok=self.cleaned_data['newsletter_ok'],
            research_ok=self.cleaned_data['research_ok']
        )
