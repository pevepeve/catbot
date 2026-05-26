from services.link_service import LinkService


def test_rewrite_twitter_status_link():
    service = LinkService("https://nitter.example/")

    rewritten = service.rewrite_twitter_link(
        "check this https://twitter.com/user/status/123456"
    )

    assert rewritten == "https://nitter.example/user/status/123456"


def test_rewrite_twitter_profile_link():
    service = LinkService("https://nitter.example/")

    rewritten = service.rewrite_twitter_link("https://twitter.com/someuser")

    assert rewritten == "https://nitter.example/someuser"


def test_rewrite_twitter_link_returns_none_without_match():
    service = LinkService("https://nitter.example/")

    rewritten = service.rewrite_twitter_link("https://example.com/no-twitter-here")

    assert rewritten is None

