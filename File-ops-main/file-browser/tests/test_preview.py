def test_text_preview_is_rendered_as_escaped_text(client, file_tree):
    (file_tree / "documents" / "unsafe.md").write_text("<script>alert(1)</script>", encoding="utf-8")

    response = client.get("/preview/documents/unsafe.md")

    assert response.status_code == 200
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in response.data


def test_image_preview_is_served_inline(client):
    response = client.get("/preview/image.png")

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("image/png")


def test_binary_file_uses_download_instead_of_text_preview(client, file_tree):
    (file_tree / "archive.bin").write_bytes(b"\x00\x01")

    response = client.get("/preview/archive.bin")

    assert response.status_code == 404