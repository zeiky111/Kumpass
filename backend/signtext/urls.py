from django.urls import path

from .views import (
    health_check,
    instructor_announcement_detail,
    instructor_announcements,
    instructor_dashboard,
    instructor_module_detail,
    instructor_modules,
    leaderboard,
    learning_state,
    login,
    module_file_detail,
    module_files,
    public_announcements,
    predict_fingerspelling,
    predict_sign,
    recent_predictions,
    signup,
)

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("auth/signup/", signup, name="auth-signup"),
    path("auth/login/", login, name="auth-login"),
    path("leaderboard/", leaderboard, name="leaderboard"),
    path("announcements/", public_announcements, name="public-announcements"),
    path("learning/state/", learning_state, name="learning-state"),
    path("instructor/dashboard/", instructor_dashboard, name="instructor-dashboard"),
    path("instructor/modules/", instructor_modules, name="instructor-modules"),
    path("instructor/modules/<int:module_id>/", instructor_module_detail, name="instructor-module-detail"),
    path("instructor/modules/<int:module_id>/files/", module_files, name="module-files"),
    path("instructor/modules/<int:module_id>/files/<int:file_id>/", module_file_detail, name="module-file-detail"),
    path("instructor/announcements/", instructor_announcements, name="instructor-announcements"),
    path("instructor/announcements/<int:announcement_id>/", instructor_announcement_detail, name="instructor-announcement-detail"),
    path("sign/predict/", predict_sign, name="predict-sign"),
    path("sign/fingerspell/", predict_fingerspelling, name="predict-fingerspelling"),
    path("sign/recent/", recent_predictions, name="recent-predictions"),
]
