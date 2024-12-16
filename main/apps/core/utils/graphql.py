from graphql import ResolveInfo


def is_authenticated(info: ResolveInfo):
    return info.context.user.is_authenticated and info.context.user.company
