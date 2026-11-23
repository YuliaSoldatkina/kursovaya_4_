from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Mailing, Message, Recipient


class RecipientForm(forms.ModelForm):
    class Meta:
        model = Recipient
        fields = ['email', 'full_name', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3}),
        }


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['subject', 'body']
        widgets = {
            'body': forms.Textarea(attrs={'rows': 5}),
        }


class MailingForm(forms.ModelForm):
    class Meta:
        model = Mailing
        fields = ['start_time', 'end_time', 'message', 'recipients']
        widgets = {
            'start_time': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'end_time': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        for field_name in ['start_time', 'end_time']:
            self.fields[field_name].input_formats = ['%Y-%m-%dT%H:%M']

        if self.user and not self.user.groups.filter(name='Менеджер').exists():
            self.fields['message'].queryset = Message.objects.filter(
                owner=self.user
            )
            self.fields['recipients'].queryset = Recipient.objects.filter(
                owner=self.user
            )

    def clean_start_time(self):
        start_time = self.cleaned_data['start_time']

        if not self.instance.pk and start_time < timezone.now():
            raise ValidationError(
                'Дата и время начала отправки не могут быть в прошлом.'
            )

        return start_time

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time and end_time and start_time >= end_time:
            raise ValidationError(
                'Дата и время начала отправки должны быть раньше даты и времени окончания.'
            )

        return cleaned_data
