from django.db.models import (
    Q,
    Exists,
    OuterRef,
    QuerySet,
    When,
    IntegerField,
    FloatField,
    Count,
    ExpressionWrapper,
    Case,
    Value,
    F,
    Prefetch,
)

from fame.models import Fame, FameLevels, FameUsers, ExpertiseAreas
from socialnetwork.models import Posts, SocialNetworkUsers


# general methods independent of html and REST views
# should be used by REST and html views


def _get_social_network_user(user) -> SocialNetworkUsers:
    """Given a FameUser, gets the social network user from the request. Assumes that the user is authenticated."""
    try:
        user = SocialNetworkUsers.objects.get(id=user.id)
    except SocialNetworkUsers.DoesNotExist:
        raise PermissionError("User does not exist")
    return user


def timeline(
    user: SocialNetworkUsers,
    start: int = 0,
    end: int = None,
    published=True,
    community_mode=False,
):
    """Get the timeline of the user. Assumes that the user is authenticated."""

    if community_mode:
        # T4c
        # in community mode, posts of communities are displayed if ALL of the following criteria are met:
        # 1. the author of the post is a member of the community
        # 2. the user is a member of the community
        # 3. the post contains the community’s expertise area
        # 4. the post is published or the user is the author

        pass
        #########################
        # add your code here
        #########################
        posts = Posts.objects.none()
        user_communities = user.communities.all()
        # get the community of the user to satisfy condition 2
        for community in user_communities:
            # get only posts of the user's comunity to satisfy condition 3
            # ensure that the author is also in that community to satisfy condition 1
            # make sure the post is published or it is the user's post
            community_posts = Posts.objects.filter(
                (Q(published=True) | Q(author=user)),
                expertise_area_and_truth_ratings=community,
                author__communities=community,
            )
            posts = posts | community_posts
    else:
        # in standard mode, posts of followed users are displayed
        _follows = user.follows.all()
        posts = Posts.objects.filter(
            (Q(author__in=_follows) & Q(published=published)) | Q(author=user)
        ).order_by("-submitted")
    if end is None:
        return posts[start:]
    else:
        return posts[start : end + 1]


def search(keyword: str, start: int = 0, end: int = None, published=True):
    """Search for all posts in the system containing the keyword. Assumes that all posts are public"""
    posts = Posts.objects.filter(
        Q(content__icontains=keyword)
        | Q(author__email__icontains=keyword)
        | Q(author__first_name__icontains=keyword)
        | Q(author__last_name__icontains=keyword),
        published=published,
    ).order_by("-submitted")
    if end is None:
        return posts[start:]
    else:
        return posts[start : end + 1]


def follows(user: SocialNetworkUsers, start: int = 0, end: int = None):
    """Get the users followed by this user. Assumes that the user is authenticated."""
    _follows = user.follows.all()
    if end is None:
        return _follows[start:]
    else:
        return _follows[start : end + 1]


def followers(user: SocialNetworkUsers, start: int = 0, end: int = None):
    """Get the followers of this user. Assumes that the user is authenticated."""
    _followers = user.followed_by.all()
    if end is None:
        return _followers[start:]
    else:
        return _followers[start : end + 1]


def follow(user: SocialNetworkUsers, user_to_follow: SocialNetworkUsers):
    """Follow a user. Assumes that the user is authenticated. If user already follows the user, signal that."""
    if user_to_follow in user.follows.all():
        return {"followed": False}
    user.follows.add(user_to_follow)
    user.save()
    return {"followed": True}


def unfollow(user: SocialNetworkUsers, user_to_unfollow: SocialNetworkUsers):
    """Unfollow a user. Assumes that the user is authenticated. If user does not follow the user anyway, signal that."""
    if user_to_unfollow not in user.follows.all():
        return {"unfollowed": False}
    user.follows.remove(user_to_unfollow)
    user.save()
    return {"unfollowed": True}


def submit_post(
    user: SocialNetworkUsers,
    content: str,
    cites: Posts = None,
    replies_to: Posts = None,
):
    """Submit a post for publication. Assumes that the user is authenticated.
    returns a tuple of three elements:
    1. a dictionary with the keys "published" and "id" (the id of the post)
    2. a list of dictionaries containing the expertise areas and their truth ratings
    3. a boolean indicating whether the user was banned and logged out and should be redirected to the login page
    """

    # create post  instance:
    post = Posts.objects.create(
        content=content,
        author=user,
        cites=cites,
        replies_to=replies_to,
    )

    # classify the content into expertise areas:
    # only publish the post if none of the expertise areas contains bullshit:
    _at_least_one_expertise_area_contains_bullshit, _expertise_areas = (
        post.determine_expertise_areas_and_truth_ratings()
    )
    post.published = not _at_least_one_expertise_area_contains_bullshit

    redirect_to_logout = False

    #########################
    # add your code here
    #########################

    # a more obtuse way to get the fame levels assosciated with each user_expertise_area
    # user_expertise_areas_fame_levels = {
    #     user_expertise.label: Fame.objects.get(
    #         user=user, expertise_area=user_expertise
    #     ).fame_level.numeric_value
    #     for user_expertise in user.expertise_area.all()
    # }

    # T1
    # get the user_expertise areas of a user
    user_expertise_areas = list(user.expertise_area.all())
    # create a dictionary mapping each user_expertise to their fame level
    user_expertise_areas_fame_levels = {}
    for user_expertise in user_expertise_areas:
        fame_level = Fame.objects.get(
            user=user, expertise_area=user_expertise
        ).fame_level.numeric_value
        user_expertise_areas_fame_levels[user_expertise] = fame_level
    for post_expertise_area in _expertise_areas:
        post_expertise_area = post_expertise_area["expertise_area"]
        # check if post expertise area is in user expertise areas
        # and check if user expertise is negative for the expertise area in question
        if (
            post_expertise_area in user_expertise_areas_fame_levels
            and user_expertise_areas_fame_levels[post_expertise_area] < 0
        ):
            post.published = False

    # T2
    for post_expertise_area in _expertise_areas:
        post_expertise_area, post_truth_rating = (
            post_expertise_area["expertise_area"],
            post_expertise_area["truth_rating"],
        )
        # T2a
        if (
            post_truth_rating
            and post_truth_rating.numeric_value < 0
            and post_expertise_area in user_expertise_areas
        ):
            try:
                user_expertise_area = post_expertise_area
                fame = Fame.objects.get(user=user, expertise_area=user_expertise_area)
                fame.fame_level = fame.fame_level.get_next_lower_fame_level()
                # T4d
                super_pro_numeric_value = FameLevels.objects.get(
                    name="Super Pro"
                ).numeric_value
                if fame.fame_level.numeric_value < super_pro_numeric_value:
                    leave_community(user, user_expertise_area)
                fame.save()
            # T2c
            except ValueError:
                user.is_active = False
                user.save()
                redirect_to_logout = True
                posts = Posts.objects.filter(author__exact=user)
                for post in posts:
                    post.published = False
                    post.save()
        # T2b
        elif (
            post_expertise_area not in user_expertise_areas
            and post_truth_rating
            and post_truth_rating.numeric_value < 0
        ):
            confuser = FameLevels.objects.get(name="Confuser")
            Fame.objects.create(
                user=user, expertise_area=post_expertise_area, fame_level=confuser
            )

    post.save()

    return (
        {"published": post.published, "id": post.id},
        _expertise_areas,
        redirect_to_logout,
    )


def rate_post(
    user: SocialNetworkUsers, post: Posts, rating_type: str, rating_score: int
):
    """Rate a post. Assumes that the user is authenticated. If user already rated the post with the given rating_type,
    update that rating score."""
    user_rating = None
    try:
        user_rating = user.userratings_set.get(post=post, rating_type=rating_type)
    except user.userratings_set.model.DoesNotExist:
        pass

    if user == post.author:
        raise PermissionError(
            "User is the author of the post. You cannot rate your own post."
        )

    if user_rating is not None:
        # update the existing rating:
        user_rating.rating_score = rating_score
        user_rating.save()
        return {"rated": True, "type": "update"}
    else:
        # create a new rating:
        user.userratings_set.add(
            post,
            through_defaults={"rating_type": rating_type, "rating_score": rating_score},
        )
        user.save()
        return {"rated": True, "type": "new"}


def fame(user: SocialNetworkUsers):
    """Get the fame of a user. Assumes that the user is authenticated."""
    try:
        user = SocialNetworkUsers.objects.get(id=user.id)
    except SocialNetworkUsers.DoesNotExist:
        raise ValueError("User does not exist")

    return user, Fame.objects.filter(user=user)


def bullshitters():
    """Return a Python dictionary mapping each existing expertise area in the fame profiles to a list of the users
    having negative fame for that expertise area. Each list should contain Python dictionaries as entries with keys
    ``user'' (for the user) and ``fame_level_numeric'' (for the corresponding fame value), and should be ranked, i.e.,
    users with the lowest fame are shown first, in case there is a tie, within that tie sort by date_joined
    (most recent first). Note that expertise areas with no expert may be omitted.
    """
    pass
    #########################
    # add your code here
    #########################

    # T3
    # get all the existing expertise areas
    existing_expertise_areas = ExpertiseAreas.objects.all()
    result = {}
    for existing_area in existing_expertise_areas:
        # get all users who have the given expertise area, but with fame_level below 0
        # make sure it is correctly ordered
        users_with_negative_fame = Fame.objects.filter(
            expertise_area__exact=existing_area, fame_level__numeric_value__lt=0
        ).order_by("-fame_level", "-user__date_joined")
        expertise_area_users = []
        for fame_entry in users_with_negative_fame:
            # put each user, fame_level pair in a dictionary, and collate all
            # this in a list for a given expertise area
            expertise_area_user = {}
            expertise_area_user["user"] = fame_entry.user
            expertise_area_user["fame_level_numeric"] = (
                fame_entry.fame_level.numeric_value
            )
            expertise_area_users.append(expertise_area_user)
        # set each existing area to this list of users
        result[existing_area] = expertise_area_users
    return result


def join_community(user: SocialNetworkUsers, community: ExpertiseAreas):
    """Join a specified community. Note that this method does not check whether the user is eligible for joining the
    community.
    """
    pass
    #########################
    # add your code here
    #########################

    # T4b
    user.communities.add(community)


def leave_community(user: SocialNetworkUsers, community: ExpertiseAreas):
    """Leave a specified community."""
    pass
    #########################
    # add your code here
    #########################

    # T4b
    user.communities.remove(community)


def similar_users(user: SocialNetworkUsers):
    """Compute the similarity of user with all other users. The method returns a QuerySet of FameUsers annotated
    with an additional field 'similarity'. Sort the result in descending order according to 'similarity', in case
    there is a tie, within that tie sort by date_joined (most recent first)"""
    pass
    #########################
    # add your code here
    #########################

    # T5
    _E_i = user.expertise_area.all()
    size_E_i = len(_E_i)

    def f(user: FameUsers, e: ExpertiseAreas) -> float:
        try:
            fame = Fame.objects.get(user=user, expertise_area=e)
            return fame.fame_level.numeric_value
        except Fame.DoesNotExist:
            return float("inf")

    def omega(f: float, f_j: float) -> int:
        return int(abs(f - f_j) <= 100)

    def s(user_j: FameUsers) -> float:
        return (1 / size_E_i) * sum([omega(f(user, e), f(user_j, e)) for e in _E_i])

    result = list(FameUsers.objects.exclude(id=user.pk))
    for user_j in result:
        user_j.similarity = s(user_j)

    result = list(filter(lambda x: x.similarity != 0, result))
    result.sort(key=lambda x: (x.similarity, x.date_joined), reverse=True)
    return result
