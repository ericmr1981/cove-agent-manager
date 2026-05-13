import pytest

from cove.harness.permissions import PermissionSystem


class TestPermissionSystem:
    """Tests for PermissionSystem tool execution permissions."""

    def test_read_permitted_by_default(self):
        ps = PermissionSystem(mode="acceptEdits")
        decision = ps.check("Read", {"file_path": "/etc/passwd"})
        assert decision.allowed is True
        assert decision.require_user_approval is False

    def test_grep_permitted_by_default(self):
        ps = PermissionSystem(mode="acceptEdits")
        decision = ps.check("Grep", {"pattern": "root"})
        assert decision.allowed is True

    def test_glob_permitted_by_default(self):
        ps = PermissionSystem(mode="acceptEdits")
        decision = ps.check("Glob", {"pattern": "*.py"})
        assert decision.allowed is True

    def test_edit_permitted_in_accept_edits_mode(self):
        ps = PermissionSystem(mode="acceptEdits")
        decision = ps.check("Edit", {"file_path": "/tmp/test.py", "old_string": "foo", "new_string": "bar"})
        assert decision.allowed is True

    def test_edit_not_permitted_in_auto_mode(self):
        ps = PermissionSystem(mode="auto")
        decision = ps.check("Edit", {"file_path": "/tmp/test.py", "old_string": "foo", "new_string": "bar"})
        assert decision.allowed is False
        assert decision.require_user_approval is True

    def test_dangerous_pattern_blocked(self):
        ps = PermissionSystem(mode="acceptEdits")
        decision = ps.check("Bash", {"command": "rm -rf /important"})
        assert decision.allowed is False
        assert decision.require_user_approval is True
        assert "Dangerous" in decision.reason

    def test_sudo_dangerous_pattern_blocked(self):
        ps = PermissionSystem(mode="acceptEdits")
        decision = ps.check("Bash", {"command": "sudo rm -rf /"})
        assert decision.allowed is False
        assert decision.require_user_approval is True

    def test_chmod_777_dangerous_pattern_blocked(self):
        ps = PermissionSystem(mode="acceptEdits")
        decision = ps.check("Bash", {"command": "chmod 777 /etc/shadow"})
        assert decision.allowed is False
        assert decision.require_user_approval is True

    def test_bypass_mode_allows_all(self):
        ps = PermissionSystem(mode="bypassPermissions")
        decision = ps.check("Bash", {"command": "rm -rf /"})
        assert decision.allowed is True
        assert decision.require_user_approval is False

    def test_bypass_mode_allows_dangerous_web_fetch(self):
        ps = PermissionSystem(mode="bypassPermissions")
        decision = ps.check("WebFetch", {"url": "file:///etc/passwd"})
        assert decision.allowed is True

    def test_auto_mode_requires_approval(self):
        ps = PermissionSystem(mode="auto")
        decision = ps.check("Bash", {"command": "ls -la"})
        assert decision.allowed is False
        assert decision.require_user_approval is True
        assert "auto mode" in decision.reason

    def test_web_fetch_localhost_blocked(self):
        ps = PermissionSystem(mode="acceptEdits")
        decision = ps.check("WebFetch", {"url": "http://localhost:8080/secret"})
        assert decision.allowed is False
        assert decision.require_user_approval is True

    def test_web_fetch_file_protocol_blocked(self):
        ps = PermissionSystem(mode="acceptEdits")
        decision = ps.check("WebFetch", {"url": "file:///etc/passwd"})
        assert decision.allowed is False
        assert decision.require_user_approval is True
