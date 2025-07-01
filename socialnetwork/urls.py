from django.urls import path

from socialnetwork.views.html import timeline
from socialnetwork.views.html import follow
from socialnetwork.views.html import unfollow
from socialnetwork.views.rest import PostsListApiView
from socialnetwork.views.html import bullshitters    #T6

app_name = "socialnetwork"

urlpatterns = [
    path("api/posts", PostsListApiView.as_view(), name="posts_fulllist"),
    path("html/timeline", timeline, name="timeline"),
    path("api/follow", follow, name="follow"),
    path("api/unfollow", unfollow, name="unfollow"),
    path("html/bullshitters", bullshitters_view, name="bullshitters"),   #T6
]
