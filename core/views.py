from django.shortcuts import render, redirect
from django.contrib.auth import login, get_user_model
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import EmailMessage
from django.http import HttpResponse
from .forms import SignUpForm
from .tokens import account_activation_token

User = get_user_model()

def home(request):
    return render(request, 'core/index.html')

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False # Deactivate account until email confirmed
            user.save()

            # Email Logic
            current_site = get_current_site(request)
            mail_subject = 'Activate your Gigs360 Account'
            message = render_to_string('registration/acc_active_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
            })
            to_email = form.cleaned_data.get('email')
            email = EmailMessage(
                mail_subject, message, to=[to_email]
            )
            email.send()

            # Return success flag to template to trigger Pop-Up
            return render(request, 'registration/signup.html', {
                'form': SignUpForm(),
                'success_popup': True # This triggers the SweetAlert
            })
    else:
        form = SignUpForm()
    
    return render(request, 'registration/signup.html', {'form': form})

def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
        
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        # Redirect to login with success message, or dashboard
        return redirect('home')
    else:
        return HttpResponse('Activation link is invalid!')