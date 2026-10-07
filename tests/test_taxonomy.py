"""Taxonomy files: what check_taxonomy refuses, and the annotator rules that come with a taxonomy."""
import copy
import pytest
from commsfail.annotators import check_annotator, check_taxonomy, registry, taxonomy_of

GOOD = {"id": "t", "version": "1", "description": "a test taxonomy",
        "groups": [{"id": "g", "name": "G", "definition": "a group"}],
        "modes": [{"id": "a", "name": "A", "group": "g", "definition": "mode a", "maps_to": ["regex_v1:B1"]},
                  {"id": "b", "name": "B", "definition": "mode b"}]}

def _broken(change):
    t = copy.deepcopy(GOOD)
    change(t)
    return t

def test_a_good_taxonomy_passes_with_and_without_the_registry():
    assert check_taxonomy(GOOD) == [] and check_taxonomy(GOOD, registry()) == []

@pytest.mark.parametrize("change,msg", [
    (lambda t: t.pop("version"), "non-empty string 'version'"),
    (lambda t: t.update(modes=[]), "non-empty list"),
    (lambda t: t["modes"].append(dict(t["modes"][1])), "mode ids must be unique"),
    (lambda t: t["modes"][1].pop("definition"), "mode 'b' needs a non-empty string 'definition'"),
    (lambda t: t["modes"][1].update(group="nowhere"), "which 'groups' does not define"),
    (lambda t: t["groups"].append(dict(t["groups"][0])), "group ids must be unique"),
    (lambda t: t["modes"][0].update(maps_to="regex_v1:B1"), "'maps_to' must be a list"),
    (lambda t: t["modes"][0].update(maps_to=["B1"]), "'maps_to' must be a list"),
])
def test_check_taxonomy_refuses(change, msg):
    errs = check_taxonomy(_broken(change))
    assert any(msg in e for e in errs), errs

@pytest.mark.parametrize("target,msg", [
    ("regex_v1:ZZ", "regex_v1's taxonomy has no mode 'ZZ'"),
    ("nobody:B1", "no installed annotator 'nobody' has a taxonomy"),
])
def test_maps_to_must_name_a_real_mode(target, msg):
    errs = check_taxonomy(_broken(lambda t: t["modes"][0].update(maps_to=[target])), registry())
    assert any(msg in e for e in errs), errs

def test_an_annotator_with_a_taxonomy_must_say_which_modes_it_reports():
    class NoModesIn:
        name, version = "no_modes_in", "0.1.0"
        schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "x", "title": "x",
                  "description": "x", "type": "object"}
        taxonomy = GOOD
        def annotate(self, trace): return {}
    assert any("modes_in" in e for e in check_annotator(NoModesIn))
    NoModesIn.modes_in = lambda self, out: []
    assert check_annotator(NoModesIn) == []

def test_facts_v1_maps_its_facts_onto_regex_v1():
    tax = taxonomy_of(registry()["facts_v1"])
    assert {m["id"]: m.get("maps_to", []) for m in tax["modes"]} == {
        "overlapping_claim": ["regex_v1:R1"], "claim_without_action": [],
        "review_without_reading": ["regex_v1:D2"], "success_without_run": ["regex_v1:D1"],
        "success_after_failure": ["regex_v1:D1"], "private_contradiction": ["regex_v1:D1"],
        "check_failed_after_done": ["regex_v1:D1"]}
