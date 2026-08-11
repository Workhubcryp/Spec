def test_download_returns_file_contents(client):
    response = client.get("/download/documents/README.md")

    assert response.status_code == 200
    assert response.data == b"# Hello\n"
    assert "attachment" in response.headers["Content-Disposition"]


def test_download_directory_is_not_allowed(client):
    response = client.get("/download/documents")

    assert response.status_code == 404