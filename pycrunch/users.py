"""
User management
===============

Sharing a dataset
-----------------

To share a dataset with an existing user, you need the user's URL.
A common way to find that is to use the list of users in your account::

    account_users = site.user_url.account_url.users
    user = account_users.by('email')["bill.carson@mycorp.com"]
    print(user.dataset_permissions)
    pycrunch.elements.JSONObject(**{
        "edit": true,
        "change_permissions": true,
        "add_users": true,
        "change_weight": true,
        "view": true
    })

Note that each user has global limitations set by their account administrator;
you may not grant them permissions to any dataset that exceed these.

To grant or permissions you want that user to have on your dataset::

    myds.permissions.edit(
        user.entity_url,
        dataset_permissions={'view': True, 'edit': True}
    )

To grant to several users at once::

    myds.permissions.edit_index({
        user1.entity_url: {"dataset_permissions": {'view': True, 'edit': True}},
        user2.entity_url: {"dataset_permissions": {'view': True}},
        user3.entity_url: {"dataset_permissions": {'view': True}},
    })

The requesting user must have the 'add_users' and/or 'change_permissions'
permissions as necessary.

You can also set initial filters or a weight, and alter or revoke permissions.
See https://crunchio.atlassian.net/wiki/display/API/permissions for more info.
"""

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

    return account.users.post(
        data=json.dumps({"element": "shoji:entity", "body": body})
    ).headers['Location']
