"""验证 harness 完整性"""
import os
import json

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

REQUIRED_FILES = [
    "CLAUDE.md",
    "AGENTS.md",
    "harness.json",
    "features.json",
    "CHANGELOG.md",
    "init.sh",
    "docs/cove-agent-manager-design.md",
    "docs/architecture.md",
    "harness/goal.md",
    "scripts/run_drift_check.sh",
    "scripts/run_change_guard.sh",
]

def test_required_files_exist():
    for f in REQUIRED_FILES:
        path = os.path.join(REPO, f)
        assert os.path.exists(path), f"Missing: {f}"

def test_features_json_is_valid():
    with open(os.path.join(REPO, "features.json")) as f:
        features = json.load(f)
    assert len(features) > 0, "features.json is empty"
    for feat in features:
        assert "id" in feat, f"Feature missing id: {feat}"
        assert "passes" in feat, f"Feature {feat.get('id')} missing passes"
        assert isinstance(feat["passes"], bool)

def test_changelog_has_content():
    with open(os.path.join(REPO, "CHANGELOG.md")) as f:
        content = f.read()
    assert "Cove" in content, "CHANGELOG missing project name"
