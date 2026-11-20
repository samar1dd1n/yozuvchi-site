from django.urls import path

from . import views

app_name = "web"

urlpatterns = [
    path("", views.home, name="home"),
    path("kitob/", views.book, name="book"),
    path("kitob/<str:slug>/", views.book, name="book-detail"),
    path("fikrlar/", views.posts, name="posts"),
    path("fikrlar/<str:slug>/", views.post_detail, name="post-detail"),
    path("robots.txt", views.robots, name="robots"),
]
