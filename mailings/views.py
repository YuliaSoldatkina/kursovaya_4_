from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from .forms import MessageForm, MailingForm, RecipientForm
from .models import Mailing, MailingAttempt, Message, Recipient


def is_manager(user):
    return user.groups.filter(name='Менеджер').exists()


class OwnerQuerysetMixin:
    def get_queryset(self):
        queryset = super().get_queryset()

        if is_manager(self.request.user):
            return queryset

        return queryset.filter(owner=self.request.user)


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'mailings/home.html'


class RecipientListView(LoginRequiredMixin, OwnerQuerysetMixin, ListView):
    model = Recipient
    template_name = 'mailings/recipient_list.html'
    context_object_name = 'recipients'


class RecipientDetailView(LoginRequiredMixin, OwnerQuerysetMixin, DetailView):
    model = Recipient
    template_name = 'mailings/recipient_detail.html'
    context_object_name = 'recipient'


class RecipientCreateView(LoginRequiredMixin, CreateView):
    model = Recipient
    form_class = RecipientForm
    template_name = 'mailings/recipient_form.html'
    success_url = reverse_lazy('mailings:recipient_list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class RecipientUpdateView(LoginRequiredMixin, OwnerQuerysetMixin, UpdateView):
    model = Recipient
    form_class = RecipientForm
    template_name = 'mailings/recipient_form.html'
    success_url = reverse_lazy('mailings:recipient_list')


class RecipientDeleteView(LoginRequiredMixin, OwnerQuerysetMixin, DeleteView):
    model = Recipient
    template_name = 'mailings/recipient_confirm_delete.html'
    success_url = reverse_lazy('mailings:recipient_list')


class MessageListView(LoginRequiredMixin, OwnerQuerysetMixin, ListView):
    model = Message
    template_name = 'mailings/message_list.html'
    context_object_name = 'messages'


class MessageDetailView(LoginRequiredMixin, OwnerQuerysetMixin, DetailView):
    model = Message
    template_name = 'mailings/message_detail.html'
    context_object_name = 'message'


class MessageCreateView(LoginRequiredMixin, CreateView):
    model = Message
    form_class = MessageForm
    template_name = 'mailings/message_form.html'
    success_url = reverse_lazy('mailings:message_list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class MessageUpdateView(LoginRequiredMixin, OwnerQuerysetMixin, UpdateView):
    model = Message
    form_class = MessageForm
    template_name = 'mailings/message_form.html'
    success_url = reverse_lazy('mailings:message_list')


class MessageDeleteView(LoginRequiredMixin, OwnerQuerysetMixin, DeleteView):
    model = Message
    template_name = 'mailings/message_confirm_delete.html'
    success_url = reverse_lazy('mailings:message_list')


class MailingListView(LoginRequiredMixin, OwnerQuerysetMixin, ListView):
    model = Mailing
    template_name = 'mailings/mailing_list.html'
    context_object_name = 'mailings'


class MailingDetailView(LoginRequiredMixin, OwnerQuerysetMixin, DetailView):
    model = Mailing
    template_name = 'mailings/mailing_detail.html'
    context_object_name = 'mailing'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        obj.update_status()
        return obj


class MailingCreateView(LoginRequiredMixin, CreateView):
    model = Mailing
    form_class = MailingForm
    template_name = 'mailings/mailing_form.html'
    success_url = reverse_lazy('mailings:mailing_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class MailingUpdateView(LoginRequiredMixin, OwnerQuerysetMixin, UpdateView):
    model = Mailing
    form_class = MailingForm
    template_name = 'mailings/mailing_form.html'
    success_url = reverse_lazy('mailings:mailing_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class MailingDeleteView(LoginRequiredMixin, OwnerQuerysetMixin, DeleteView):
    model = Mailing
    template_name = 'mailings/mailing_confirm_delete.html'
    success_url = reverse_lazy('mailings:mailing_list')


class MailingSendView(LoginRequiredMixin, View):
    def post(self, request, pk):
        mailing = get_object_or_404(
            Mailing,
            pk=pk,
            owner=request.user,
        )
        mailing.update_status()

        now = timezone.now()

        if not (mailing.start_time <= now <= mailing.end_time):
            messages.error(
                request,
                'Отправка рассылки недоступна: текущее время вне периода рассылки.'
            )
            return redirect('mailings:mailing_detail', pk=mailing.pk)

        recipients = mailing.recipients.all()
        attempts = []

        for recipient in recipients:
            try:
                send_mail(
                    subject=mailing.message.subject,
                    message=mailing.message.body,
                    from_email=None,
                    recipient_list=[recipient.email],
                    fail_silently=False,
                )
                attempts.append(
                    MailingAttempt(
                        mailing=mailing,
                        status=MailingAttempt.STATUS_SUCCESS,
                        server_response='Письмо успешно отправлено.',
                    )
                )
            except Exception as error:
                attempts.append(
                    MailingAttempt(
                        mailing=mailing,
                        status=MailingAttempt.STATUS_FAILED,
                        server_response=str(error),
                    )
                )

        if attempts:
            MailingAttempt.objects.bulk_create(attempts)

        messages.success(
            request,
            f'Рассылка обработана. Создано попыток отправки: {len(attempts)}.'
        )
        return redirect('mailings:mailing_detail', pk=mailing.pk)


@method_decorator(cache_page(60), name='dispatch')
@method_decorator(vary_on_headers('Cookie'), name='dispatch')
class StatisticsView(LoginRequiredMixin, TemplateView):
    template_name = 'mailings/statistics.html'

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        response['Cache-Control'] = 'public, max-age=60'
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        cache_key = f'statistics_user_{self.request.user.pk}'
        statistics = cache.get(cache_key)

        if statistics is None:
            user_mailings = Mailing.objects.filter(owner=self.request.user)
            active_mailings = user_mailings.filter(
                start_time__lte=timezone.now(),
                end_time__gte=timezone.now(),
                status=Mailing.STATUS_STARTED,
            )

            successful_attempts = MailingAttempt.objects.filter(
                mailing__owner=self.request.user,
                status=MailingAttempt.STATUS_SUCCESS,
            ).count()

            failed_attempts = MailingAttempt.objects.filter(
                mailing__owner=self.request.user,
                status=MailingAttempt.STATUS_FAILED,
            ).count()

            statistics = {
                'total_mailings': user_mailings.count(),
                'active_mailings': active_mailings.count(),
                'total_recipients': Recipient.objects.filter(
                    owner=self.request.user
                ).count(),
                'successful_attempts': successful_attempts,
                'failed_attempts': failed_attempts,
                'sent_messages': successful_attempts,
            }

            cache.set(cache_key, statistics, 60)

        context['statistics'] = statistics
        return context
