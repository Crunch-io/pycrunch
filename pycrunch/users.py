import json


def invite(account, email, send_invite=None, url_base=None, id_method=None,
           role_url=None, account_permissions=None, **body):
    """Invite a new user directly to the given account. Return the new URL.

    id_method may be one of 'pwhash' (the default) or 'oauth'.
    role_url, if present, must be one of site.roles.accounts.
    """

    body['email'] = email
    if send_invite is not None:
        body['send_invite'] = send_invite
    if url_base is not None:
        body['url_base'] = url_base
    if id_method is not None:
        body['id_method'] = id_method
    if role_url is not None:
        body['role_url'] = role_url
    if account_permissions is not None:
        body['account_permissions'] = account_permissions

    return account.users_url.post(
        data=json.dumps({"element": "shoji:entity", "body": body})
    ).headers['Location']
