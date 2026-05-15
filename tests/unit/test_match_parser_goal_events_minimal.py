from besoccer_scraper.infrastructure.parsers.match_parser import MatchParser


def test_goal_events_minimal():
    html = '''<section id="events-goals">23' Madson goal 35' Iván González goal 47' Puma Rodríguez goal</section>'''
    events = MatchParser()._extract_events({}, html)
    assert len(events) == 3
    assert [e["minute"] for e in events] == [23, 35, 47]


def test_goal_events_prioritize_events_goals_over_timeline_and_dedupe():
    html = '''<section id="events-goals">23' Madson goal 35' Iván González goal 47' Puma Rodríguez goal 47' Puma Rodríguez goal</section>'''
    payload = {
        "timeline": [
            {"type": "goal", "minute": "10", "player": "Ignored Goal"},
            {"type": "yellow_card", "minute": "11", "player": "Ignored Card"},
        ]
    }

    events = MatchParser()._extract_events(payload, html)

    assert len(events) == 3
    assert [e["minute"] for e in events] == [23, 35, 47]
    assert [e["player_name"] for e in events] == ["Madson", "Iván González", "Puma Rodríguez"]


def test_goal_events_json_strict_goal_filter_and_unknown_team_side():
    payload = {
        "timeline": [
            {"type": "goal", "minute": "12", "player": "Scorer A", "team": "home"},
            {"type": "yellow_card", "minute": "13", "player": "Not Goal"},
            {"type": "substitution", "minute": "14", "player": "Not Goal 2"},
            {"type": "goal", "minute": "15", "text": "15' Scorer B goal"},
        ]
    }
    events = MatchParser()._extract_events(payload, "<html></html>")

    assert len(events) == 2
    assert [e["player_name"] for e in events] == ["Scorer A", "Scorer B"]
    assert [e["team_side"] for e in events] == ["home", "unknown"]


def test_goal_events_text_fallback_only_when_no_rows():
    html = """<section id='events-goals'>23' Madson goal 35' Iván González goal</section>"""
    events = MatchParser()._extract_events({}, html)
    assert len(events) == 2
    assert [e["player_name"] for e in events] == ["Madson", "Iván González"]


def test_goal_events_real_html_rows_preferred_over_text():
    html = """
    <section id="events-goals">
      10' Texto Ignorado goal
      <div class="table-played-match left"><span class="min">23</span><img alt="Gol"/><a data-cy="event">Madson</a></div>
      <div class="table-played-match right"><span class="min">35</span><img src="accion1.png"/><a data-cy="event">Iván González</a></div>
    </section>
    """
    events = MatchParser()._extract_events({}, html)
    assert len(events) == 2
    assert [e["minute"] for e in events] == [23, 35]


def test_goal_events_no_substitutions_as_goals():
    html = """<section id="events-goals">23' Sustituciones goal 24' Madson goal</section>"""
    events = MatchParser()._extract_events({}, html)
    assert len(events) == 1
    assert events[0]["player_name"] == "Madson"


def test_goal_player_name_clean():
    html = """<section id="events-goals">45+2' +2 goal 47' <b>Puma Rodríguez</b> goal</section>"""
    events = MatchParser()._extract_events({}, html)
    assert len(events) == 1
    assert events[0]["player_name"] == "Puma Rodríguez"
