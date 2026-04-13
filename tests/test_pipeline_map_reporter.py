"""Tests for pipewatch.pipeline_map_reporter."""
import json

from pipewatch.pipeline_map import PipelineMap
from pipewatch.pipeline_map_reporter import PipelineMapReporter


def _make_reporter() -> PipelineMapReporter:
    pm = PipelineMap()
    pm.add_stage("ingest")
    pm.add_stage("validate", depends_on=["ingest"])
    pm.add_stage("load", depends_on=["validate"])
    return PipelineMapReporter(pm)


class TestPipelineMapReporterText:
    def test_empty_map_message(self):
        reporter = PipelineMapReporter(PipelineMap())
        assert "No pipeline stages" in reporter.format_text()

    def test_has_stages_false_when_empty(self):
        reporter = PipelineMapReporter(PipelineMap())
        assert reporter.has_stages() is False

    def test_has_stages_true_when_populated(self):
        reporter = _make_reporter()
        assert reporter.has_stages() is True

    def test_contains_stage_names(self):
        text = _make_reporter().format_text()
        assert "ingest" in text
        assert "validate" in text
        assert "load" in text

    def test_depends_on_label_present(self):
        text = _make_reporter().format_text()
        assert "depends on" in text

    def test_feeds_into_label_present(self):
        text = _make_reporter().format_text()
        assert "feeds into" in text

    def test_root_has_none_upstream(self):
        text = _make_reporter().format_text()
        # ingest has no dependencies
        assert "(none)" in text


class TestPipelineMapReporterJson:
    def test_returns_valid_json(self):
        output = _make_reporter().format_json()
        data = json.loads(output)
        assert "pipeline_map" in data

    def test_json_contains_all_stages(self):
        data = json.loads(_make_reporter().format_json())
        names = [s["name"] for s in data["pipeline_map"]]
        assert set(names) == {"ingest", "validate", "load"}

    def test_json_upstream_correct(self):
        data = json.loads(_make_reporter().format_json())
        validate = next(s for s in data["pipeline_map"] if s["name"] == "validate")
        assert validate["depends_on"] == ["ingest"]

    def test_json_downstream_correct(self):
        data = json.loads(_make_reporter().format_json())
        ingest = next(s for s in data["pipeline_map"] if s["name"] == "ingest")
        assert ingest["feeds_into"] == ["validate"]

    def test_empty_map_returns_empty_list(self):
        reporter = PipelineMapReporter(PipelineMap())
        data = json.loads(reporter.format_json())
        assert data["pipeline_map"] == []
