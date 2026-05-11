from besoccer_scraper.infrastructure.parsers.match_parser import MatchParser


def test_goal_events_minimal():
    html = '''<section id="events-goals">23' Madson goal 35' Iván González goal 47' Puma Rodríguez goal</section>'''
    events = MatchParser()._extract_events({}, html)
    assert len(events) == 3
    assert [e["minute"] for e in events] == [23, 35, 47]
