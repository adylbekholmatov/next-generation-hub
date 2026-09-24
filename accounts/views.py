from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from .forms import LoginForm, ProfileForm, StyledPasswordChangeForm


class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class LogoutView(auth_views.LogoutView):
    pass


class PasswordChangeView(auth_views.PasswordChangeView):
    template_name = "accounts/password_change.html"
    form_class = StyledPasswordChangeForm
    success_url = reverse_lazy("accounts:profile")
    extra_context = {"page_title": gettext_lazy("Change password"), "nav_active": "profile"}

    def form_valid(self, form):
        messages.success(self.request, _("Password changed."))
        return super().form_valid(form)


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Profile saved."))
        return redirect("accounts:profile")
    return render(
        request,
        "accounts/profile.html",
        {"form": form, "page_title": _("Profile"), "nav_active": "profile"},
    )
