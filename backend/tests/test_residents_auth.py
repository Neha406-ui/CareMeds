def test_residents_requires_auth(test_client):
    resp = test_client.get('/api/residents')
    assert resp.status_code == 401
