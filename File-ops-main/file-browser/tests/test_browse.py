def test_root_lists_directories_and_files(client):
    response = client.get("/browse/")

    assert response.status_code == 200
    assert b"documents/" in response.data
    assert b"image.png" in response.data


def test_can_browse_child_and_return_to_parent(client):
    response = client.get("/browse/documents")

    assert response.status_code == 200
    assert b"README.md" in response.data
    assert b"Parent directory" in response.data


def test_sort_query_is_supported(client):
    response = client.get("/browse/documents?sort=modified&order=desc")

    assert response.status_code == 200