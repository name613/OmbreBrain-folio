from utils import redact_sensitive_text


def test_redacts_bearer_and_labeled_secrets():
    text = (
        "认证: Bearer wb_1234567890abcdef\n"
        "API Key: sk-example123456789\n"
        "密码: qiqi2026"
    )

    result = redact_sensitive_text(text)

    assert "wb_1234567890abcdef" not in result
    assert "sk-example123456789" not in result
    assert "qiqi2026" not in result
    assert result.count("[REDACTED]") == 3


def test_redacts_credentials_embedded_in_url():
    result = redact_sensitive_text(
        "rtsp://camera_user:camera_password@192.0.2.10:554/stream1"
    )

    assert result == "rtsp://[REDACTED]@192.0.2.10:554/stream1"


def test_keeps_non_secret_token_discussion():
    text = "讨论 token 浪费与 API key 配置方法，不包含实际值。"

    assert redact_sensitive_text(text) == text
