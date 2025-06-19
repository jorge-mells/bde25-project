from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.db.models import Q

from socialnetwork import api
from socialnetwork.api import _get_social_network_user
from fame.models import FameLevels
from socialnetwork.models import SocialNetworkUsers, ExpertiseAreas
from socialnetwork.serializers import PostsSerializer


@require_http_methods(["GET"])
@login_required
def timeline(request):
    # using the serializer to get the data, then use JSON in the template!
    # avoids having to do the same thing twice

    # initialize community mode to False the first time in the session
    if "community_mode" not in request.session:
        request.session["community_mode"] = False

    # get extra URL parameters:
    keyword = request.GET.get("search", "")
    published = request.GET.get("published", True)
    error = request.GET.get("error", None)
    mode = {}
    mode["actual"] = (
        "Community Mode" if request.session["community_mode"] else "Standard Mode"
    )
    mode["alternate"] = (
        "Standard Mode" if request.session["community_mode"] else "Community Mode"
    )
    communities = {}
    superpro_value = FameLevels.objects.get(name="Super Pro").numeric_value
    social_user = _get_social_network_user(request.user)
    communities["join_communities"] = social_user.expertise_area.filter(
        fame__fame_level__numeric_value__gte=superpro_value
    ).all()
    communities["leave_communities"] = social_user.communities.all()
    communities["join_communities"] = communities["join_communities"].difference(
        communities["leave_communities"]
    )

    # if keyword is not empty, use search method of API:
    if keyword and keyword != "":
        context = {
            "posts": PostsSerializer(
                api.search(keyword, published=published), many=True
            ).data,
            "searchkeyword": keyword,
            "mode": mode,
            "communities": communities,
            "error": error,
            "followers": list(
                api.follows(_get_social_network_user(request.user)).values_list(
                    "id", flat=True
                )
            ),
        }
    else:  # otherwise, use timeline method of API:
        context = {
            "posts": PostsSerializer(
                api.timeline(
                    _get_social_network_user(request.user),
                    published=published,
                    community_mode=request.session["community_mode"],
                ),
                many=True,
            ).data,
            "searchkeyword": "",
            "mode": mode,
            "communities": communities,
            "error": error,
            "followers": list(
                api.follows(_get_social_network_user(request.user)).values_list(
                    "id", flat=True
                )
            ),
        }

    return render(request, "timeline.html", context=context)


@require_http_methods(["POST"])
@login_required
def follow(request):
    user = _get_social_network_user(request.user)
    user_to_follow = SocialNetworkUsers.objects.get(id=request.POST.get("user_id"))
    api.follow(user, user_to_follow)
    return redirect(reverse("sn:timeline"))


@require_http_methods(["POST"])
@login_required
def unfollow(request):
    user = _get_social_network_user(request.user)
    user_to_unfollow = SocialNetworkUsers.objects.get(id=request.POST.get("user_id"))
    api.unfollow(user, user_to_unfollow)
    return redirect(reverse("sn:timeline"))


@require_http_methods(["GET"])
@login_required
def bullshitters(request):
    bullshitters = api.bullshitters()
    return render(request, "bullshitters.html", {"bullshitters": bullshitters})


@require_http_methods(["POST"])
@login_required
def toggle_community_mode(request):
    if "community_mode" in request.session:
        request.session["community_mode"] = not request.session["community_mode"]
    else:
        request.session["community_mode"] = True
    return redirect(reverse("sn:timeline"), request=request)


@require_http_methods(["POST"])
@login_required
def join_community(request):
    community = request.POST.get("community")
    community = ExpertiseAreas.objects.get(label=community)
    user = _get_social_network_user(request.user)
    api.join_community(user, community)
    return redirect(reverse("sn:timeline"))


@require_http_methods(["POST"])
@login_required
def leave_community(request):
    community = request.POST.get("community")
    community = ExpertiseAreas.objects.get(label=community)
    user = _get_social_network_user(request.user)
    api.leave_community(user, community)
    return redirect(reverse("sn:timeline"))


@require_http_methods(["GET"])
@login_required
def similar_users(request):
    similar_users = api.similar_users(request.user)
    return render(request, "similar_users.html", {"similar_users": similar_users})
