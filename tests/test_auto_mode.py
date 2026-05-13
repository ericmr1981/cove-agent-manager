from cove.harness.auto_mode import classify_command


class TestClassifyCommand:
    """Tests for auto-mode command classification."""

    def test_classify_safe_command(self):
        result = classify_command("ls -la")
        assert result["decision"] == "allow"
        assert "safe" in result["reason"]

    def test_classify_cat(self):
        result = classify_command("cat /etc/passwd")
        assert result["decision"] == "allow"

    def test_classify_echo(self):
        result = classify_command("echo hello")
        assert result["decision"] == "allow"

    def test_classify_pwd(self):
        result = classify_command("pwd")
        assert result["decision"] == "allow"

    def test_classify_cd(self):
        result = classify_command("cd /tmp")
        assert result["decision"] == "allow"

    def test_classify_pip_install(self):
        result = classify_command("pip install requests")
        assert result["decision"] == "allow"

    def test_classify_pytest(self):
        result = classify_command("pytest tests/")
        assert result["decision"] == "allow"

    def test_classify_dangerous_rm_rf(self):
        result = classify_command("rm -rf /")
        assert result["decision"] == "block"
        assert "dangerous" in result["reason"]

    def test_classify_sudo_command(self):
        result = classify_command("sudo rm -rf /etc")
        assert result["decision"] == "block"

    def test_classify_chmod_777(self):
        result = classify_command("chmod 777 /etc/shadow")
        assert result["decision"] == "block"

    def test_classify_sql_injection_drop(self):
        result = classify_command("DROP TABLE users;")
        assert result["decision"] == "block"

    def test_classify_sql_delete_from(self):
        result = classify_command("DELETE FROM accounts")
        assert result["decision"] == "block"

    def test_classify_sql_truncate(self):
        result = classify_command("TRUNCATE users")
        assert result["decision"] == "block"

    def test_classify_unknown_command(self):
        result = classify_command("some_weird_command")
        assert result["decision"] == "ask"
        assert "Unknown" in result["reason"]

    def test_classify_empty_string(self):
        result = classify_command("")
        assert result["decision"] == "ask"

    def test_classify_case_insensitive_dangerous(self):
        result = classify_command("DROP table users")
        assert result["decision"] == "block"

    def test_classify_git_status_safe(self):
        result = classify_command("git status")
        assert result["decision"] == "allow"

    def test_classify_git_diff_safe(self):
        result = classify_command("git diff")
        assert result["decision"] == "allow"
