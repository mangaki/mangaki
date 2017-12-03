from django import forms
from mangaki.models import Suggestion, Rating
from mangaki.utils.ratings import get_anonymous_ratings, clear_anonymous_ratings


class SuggestionForm(forms.ModelForm):
    class Meta:
        model = Suggestion
        fields = ['work', 'problem', 'message']
        widgets = {'work': forms.HiddenInput()}


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
