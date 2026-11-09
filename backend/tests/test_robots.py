from dijitalvatan.crawler.robots import RobotsPolicy, parse_robots

SEED = "https://www.tsk.gov.tr/"


def test_agent_specificity_duplicate_groups_comments_and_delay():
    policy = parse_robots("""
User-agent: *
Disallow: /
Crawl-delay: 2
User-agent: DijitalVatanBot
Disallow: /gizli
Allow: /gizli/acik
Crawl-delay: 3.5
User-agent: dijitalvatanbot
Disallow: /ikinci # açıklama
Crawl-delay: 5
User-agent: AnotherBot
Disallow: /duyuru
""")
    assert policy.delay_ms == 5000
    assert len(policy.rules) == 3
    assert policy.allows(f"{SEED}duyuru")
    assert not policy.allows(f"{SEED}gizli/dosya")
    assert policy.allows(f"{SEED}gizli/acik/sayfa")
    assert not policy.allows(f"{SEED}ikinci")
    assert parse_robots("User-agent: *\nDisallow:\n").allows(SEED)


def test_longest_path_allow_ties_wildcards_anchors_and_escaped_unicode():
    policy = parse_robots("""User-agent: *
Disallow: /*.pdf$
Disallow: /arama?*
Allow: /arama?q=acik$
Disallow: /same
Allow: /same
Disallow: /Türkçe
Disallow: /%7Esecret
""")
    assert not policy.allows(f"{SEED}d.pdf")
    assert policy.allows(f"{SEED}d.pdf?ok=1")
    assert not policy.allows(f"{SEED}arama?q=kapali")
    assert policy.allows(f"{SEED}arama?q=acik")
    assert policy.allows(f"{SEED}same")
    assert not policy.allows(f"{SEED}T%C3%BCrk%C3%A7e")
    assert not policy.allows(f"{SEED}~secret")


def test_policy_round_trips_through_json():
    policy = parse_robots("User-agent: *\nDisallow: /x\nCrawl-delay: 4\n")
    assert RobotsPolicy.from_json(policy.to_json()) == policy
