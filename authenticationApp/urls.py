from django.urls import path
from authenticationApp.views import UserSignupViews, UserLoginViews, LogoutView, ChangePasswordView, ResetPasswordView, \
    ForgotPasswordView, GetAllUsers, ProfileView

urlpatterns = [
    path("signup/", UserSignupViews.as_view(), name="signup"),
    path("login/", UserLoginViews.as_view(), name="login"),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('change/password/', ChangePasswordView.as_view(), name='change-password'),
    path('forget/password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset/password/', ResetPasswordView.as_view(), name='reset-password'),

    path("users/", GetAllUsers.as_view(), name="users"),

    path("profile/", ProfileView.as_view(), name="user-profile"),
]

