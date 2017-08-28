from django import forms
from mangaki.models import Suggestion, Rating
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
    import_ratings = forms.BooleanField(required=False, initial=True, label="Importer mes notes")

    def signup(self, request, user):
        if self.cleaned_data['import_ratings']:
            ratings = get_anonymous_ratings(request.session)
            clear_anonymous_ratings(request.session)
            Rating.objects.bulk_create([
                Rating(user=user, work_id=work_id, choice=choice)
                for work_id, choice in ratings.items()
            ])
