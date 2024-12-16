from rest_framework import permissions

class SlackVerify(permissions.BasePermission):
    """
    Global slack signing verification
    """
    slack_notify = SlackNotification(verify=True)

    def has_permission(self, request, view):
        if not self.slack_notify.signature_verifier.is_valid_request(self.request.body, request.headers):
            return False
        return True
