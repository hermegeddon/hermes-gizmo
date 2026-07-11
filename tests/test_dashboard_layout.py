import json
import subprocess
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DIR = REPO_ROOT / "dashboard"
DIST_DIR = DASHBOARD_DIR / "dist"
MANIFEST = DASHBOARD_DIR / "manifest.json"
PLUGIN_ROOT = REPO_ROOT / "dashboard-plugin" / "gizmo"


class TestDashboardAssetLayout:
    """The canonical dashboard and plugin manifests resolve one Gizmo surface."""

    def test_manifest_exists_and_valid(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        assert data["name"] == "gizmo"
        assert data["tab"]["path"] == "/gizmo"
        assert data["entry"] == "dist/index.js"
        assert data["css"] == "dist/style.css"
        assert data["api"] == "plugin_api.py"

    def test_manifest_assets_exist(self):
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        assert (DASHBOARD_DIR / data["entry"]).is_file()
        assert (DASHBOARD_DIR / data["css"]).is_file()

    def test_nested_dashboard_dist_is_not_tracked(self):
        nested_dist = PLUGIN_ROOT / "dashboard" / "dist"
        result = subprocess.run(
            ["git", "ls-files", str(nested_dist)],
            capture_output=True,
            check=True,
            text=True,
            cwd=REPO_ROOT,
        )
        assert result.stdout.strip() == ""

    def test_gizmo_dashboard_plugin_is_complete(self):
        assert (PLUGIN_ROOT / "__init__.py").is_file()
        assert (PLUGIN_ROOT / "plugin.yaml").is_file()
        assert (PLUGIN_ROOT / "dashboard" / "manifest.json").is_file()
        assert (PLUGIN_ROOT / "dashboard" / "plugin_api.py").is_file()

    def test_nested_manifest_matches_canonical_identity(self):
        root_manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        nested_manifest = json.loads(
            (PLUGIN_ROOT / "dashboard" / "manifest.json").read_text(encoding="utf-8")
        )
        assert nested_manifest == root_manifest

    def test_root_and_nested_plugin_manifests_match(self):
        root_plugin = yaml.safe_load((REPO_ROOT / "plugin.yaml").read_text(encoding="utf-8"))
        nested_plugin = yaml.safe_load((PLUGIN_ROOT / "plugin.yaml").read_text(encoding="utf-8"))
        assert nested_plugin == root_plugin
        assert root_plugin["name"] == "gizmo"

    def test_dashboard_bundle_uses_canonical_routes_and_classes(self):
        javascript = (DIST_DIR / "index.js").read_text(encoding="utf-8")
        stylesheet = (DIST_DIR / "style.css").read_text(encoding="utf-8")
        assert "/api/plugins/gizmo/status" in javascript
        assert "Gizmo" in javascript
        assert "gizmo-page" in javascript
        assert ".gizmo-page" in stylesheet

    def test_installer_references_canonical_dist(self):
        script = (REPO_ROOT / "scripts" / "install-hermes-gizmo.sh").read_text(encoding="utf-8")
        assert 'DASHBOARD_SRC="$ROOT_DIR/dashboard"' in script
        assert '"$DASHBOARD_SRC/dist/index.js"' in script
        assert '"$DASHBOARD_SRC/dist/style.css"' in script

    def test_pyproject_includes_dashboard_assets_and_plugin(self):
        text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        assert '"/dashboard/dist/index.js"' in text
        assert '"/dashboard/dist/style.css"' in text
        wheel_section = text.split("[tool.hatch.build.targets.wheel]")[-1]
        assert '"/dashboard"' in wheel_section
        assert '"/dashboard-plugin"' in wheel_section
