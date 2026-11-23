from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from .forms import SignUpForm


def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)

        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            current_site = get_current_site(request)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)

            confirmation_link = (
                f'http://{current_site.domain}/accounts/activate/{uid}/{token}/'
            )

            send_mail(
                subject='Подтвердите email',
                message=(
                    f'Здравствуйте, {user.username}!\n\n'
                    f'Подтвердите свой email по ссылке:\n{confirmation_link}'
                ),
                from_email=None,
                recipient_list=[user.email],
                fail_silently=False,
            )

            return render(
                request,
                'registration/signup_done.html',
                {'email': user.email},
            )
    else:
        form = SignUpForm()

    return render(request, 'registration/signup.html', {'form': form})


def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return render(request, 'registration/email_confirmed.html')

    return render(request, 'registration/email_confirmed.html')
