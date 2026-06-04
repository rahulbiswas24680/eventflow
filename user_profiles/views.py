from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import CustomUser as User, Role


def user_register(request):
    """
    Register a new user (template-based)
    """
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")

        if not (username and email and password):
            messages.error(request, "Username, email, and password are required.")
            return redirect("user-register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect("user-register")
        
        # Get attendee role object first 
        role_obj = Role.objects.get(name='attendee')
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            current_role=role_obj
        )
        user.available_roles.add(role_obj)
        messages.success(request, "User registered successfully. Please log in.")
        return redirect("user-login")

    return render(request, "user_profiles/register.html")


def user_login(request):
    """
    Login a user with username/email and password (template-based)
    """
    if request.method == "POST":
        username_or_email = request.POST.get("username") or request.POST.get("email")
        password = request.POST.get("password")

        if not (username_or_email and password):
            messages.error(request, "Username/email and password are required.")
            return redirect("user-login")

        # allow login with email or username
        if "@" in username_or_email:
            try:
                user = User.objects.get(email=username_or_email)
                username_or_email = user.username
            except User.DoesNotExist:
                messages.error(request, "Invalid email or password.")
                return redirect("user-login")

        user = authenticate(request, username=username_or_email, password=password)
        print('user--', user)
        if user is not None:
            login(request, user)
            messages.success(request, "Login successful!")
            return redirect("events-home")  # or wherever you want
        else:
            messages.error(request, "Invalid credentials.")
            return redirect("user-login")

    return render(request, "user_profiles/login.html")


def user_logout(request):
    """
    Logout the current user
    """
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect("user-login")


@login_required
def user_profile_update(request):
    """
    Update profile for logged-in user
    """
    if request.method == "POST":
        user = request.user
        user.phone = request.POST.get("phone", user.phone)
        user.profession = request.POST.get("profession", user.profession)
        user.education = request.POST.get("education", user.education)
        user.goal = request.POST.get("goal", user.goal)
        user.languages = request.POST.get("languages", user.languages)
        user.address = request.POST.get("address", user.address)
        user.country = request.POST.get("country", user.country)
        
        # Handle image upload
        new_image = request.FILES.get('image')
        if new_image:
            # Delete old image if exists
            if user.image:
                user.image.delete(save=False)
            user.image = new_image
        
        # Only update specific fields for efficiency
        user.save(update_fields=[
            'phone', 'profession', 'education', 'goal', 
            'languages', 'address', 'country', 'image'
        ])

        messages.success(request, "Profile updated successfully.")
        return redirect("user-profile-update")

    return render(request, "user_profiles/profile_update.html")
