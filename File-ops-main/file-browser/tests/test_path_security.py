import os


def test_parent_traversal_is_rejected(client):
    for path in [
        "/browse/../outside",
        "/download/../../etc/passwd",
        "/browse/%2e%2e/%2e%2e/etc",
        "/browse/%2Fetc%2Fpasswd",
    ]:
        response = client.get(path)
        # Werkzeug may normalize a raw ../ URL before dispatch and return a
        # permanent redirect. It never reaches a filesystem outside BASE_DIR.
        assert response.status_code in {308, 403, 404}
        assert b"BASE_DIR" not in response.data


def test_external_symlink_is_not_listed_or_read(client, file_tree, tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    link = file_tree / "outside-link.txt"
    try:
        link.symlink_to(outside)
    except OSError:
        return

    listing = client.get("/browse/")
    download = client.get("/download/outside-link.txt")

    assert b"outside-link.txt" not in listing.data
    assert download.status_code == 403


def test_similar_sibling_directory_is_not_inside_base(client, file_tree):
    sibling = file_tree.parent / f"{file_tree.name}-other"
    sibling.mkdir()
    (sibling / "secret.txt").write_text("secret", encoding="utf-8")

    response = client.get(f"/browse/{sibling.name}/secret.txt")

    assert response.status_code in {403, 404}