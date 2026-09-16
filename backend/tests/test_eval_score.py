from eval.bean_extract.score import markdown_report, normalize, overall, score


def test_normalize_absorbs_only_known_spelling_differences():
    assert normalize("  Fully   Washed ") == "washed"
    assert normalize("워시드") == "washed"
    assert normalize("에티오피아") == normalize("Ethiopia")
    assert normalize("") is None
    assert normalize("Washed Anaerobic") == "washed anaerobic"


def test_invented_values_are_counted_separately_from_missed_ones():
    expected = {"name": "구지", "country": "Ethiopia", "region": None, "variety": None}
    predicted = {"name": "구지", "country": None, "region": "Guji", "variety": "Heirloom"}

    scores = score([(expected, predicted)])

    assert scores["name"].correct == 1
    assert scores["country"].missed == 1
    assert scores["region"].invented == 1
    assert scores["variety"].invented == 1
    assert overall(scores).invented == 2


def test_report_lists_each_model():
    scores = score([({"name": "a"}, {"name": "a"})])
    report = markdown_report({"model-a": scores, "model-b": scores}, {"model-b": ["001.jpg: 429"]}, n_images=1)
    assert "| model-a |" in report
    assert "001.jpg: 429" in report
