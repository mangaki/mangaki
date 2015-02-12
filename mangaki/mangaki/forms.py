from django.forms import ModelForm, HiddenInput
from mangaki.models import Suggestion

class SuggestionForm(ModelForm):
    class Meta:
        model = Suggestion
        fields = ['work', 'problem', 'message']
        widgets = {'work': HiddenInput()}