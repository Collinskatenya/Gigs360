from django.shortcuts import render, redirect
from django.contrib.auth import login, get_user_model
from django.contrib.auth.decorators import login_required
from .forms import SignUpForm

User = get_user_model()

def home(request):
    return render(request, 'core/index.html')

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # CRITICAL FIX: Set active to True so they can login immediately
            user.is_active = True 
            user.save()
            
            # Log the user in directly
            login(request, user)
            
            # Redirect to dashboard
            return redirect('dashboard')
    else:
        form = SignUpForm()
    
    return render(request, 'registration/signup.html', {'form': form})

@login_required
def dashboard(request):
    user = request.user
    # Fallback if account_type is somehow missing
    role = getattr(user, 'account_type', 'freelancer')
    
    context = {
        'role': role,
        'role_label': role.title(),
        'user': user,
    }

    # 1. FREELANCER DATA
    if role == 'freelancer':
        context.update({
            'stat_1_label': 'Upcoming Gigs', 'stat_1_value': '0', 'stat_1_icon': 'bi-calendar-event',
            'stat_2_label': 'Pending Pay',   'stat_2_value': 'KES 0.00', 'stat_2_icon': 'bi-hourglass-split',
            'stat_3_label': 'Profile Views', 'stat_3_value': '0', 'stat_3_icon': 'bi-eye',
            'todo_list': ['Complete Profile', 'Upload Portfolio']
        })

    # 2. VENDOR DATA
    elif role == 'vendor':
        context.update({
            'stat_1_label': 'Items Rented',  'stat_1_value': '0 / 0', 'stat_1_icon': 'bi-camera-video',
            'stat_2_label': 'Revenue',       'stat_2_value': 'KES 0.00', 'stat_2_icon': 'bi-cash-stack',
            'stat_3_label': 'Overdue',       'stat_3_value': '0 Items', 'stat_3_icon': 'bi-exclamation-triangle',
            'todo_list': ['Add Inventory Items', 'Verify Business Details']
        })

    # 3. AGENCY DATA
    elif role == 'agency':
        context.update({
            'stat_1_label': 'Active Events', 'stat_1_value': '0', 'stat_1_icon': 'bi-building',
            'stat_2_label': 'Talent Hired',  'stat_2_value': '0', 'stat_2_icon': 'bi-people',
            'stat_3_label': 'Budget Spent',  'stat_3_value': 'KES 0.00', 'stat_3_icon': 'bi-pie-chart',
            'todo_list': ['Create First Event', 'Invite Vendors']
        })

    return render(request, 'core/dashboard_home.html', context)

# This view is no longer needed since we removed email verification for now
def activate(request, uidb64, token):
    return redirect('home')