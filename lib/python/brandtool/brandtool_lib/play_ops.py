"""Google Play Developer API checks (audit-only; brandtool never writes to Play)."""

APP_OK, APP_MISSING, NO_ACCESS = 'ok', 'missing', 'no_access'


def check_app(publisher, package_name):
    """Probe that the app exists in the linked Play developer account.

    Creates and immediately deletes a draft edit - no visible effect. The linked
    service account needs edit permission on the app for the probe to succeed.
    """
    try:
        edit = publisher.edits().insert(packageName=package_name, body={}).execute()
        publisher.edits().delete(packageName=package_name, editId=edit['id']).execute()
        return APP_OK, ''
    except Exception as e:
        msg = str(e)
        if '404' in msg:
            return APP_MISSING, f'no app with package {package_name} in the linked Play account'
        if '403' in msg or '401' in msg:
            return NO_ACCESS, 'Play service account lacks permission (or app not visible to it)'
        raise
