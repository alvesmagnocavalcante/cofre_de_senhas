from .access import can_administer, get_membership


# Disponibiliza a permissão administrativa nos templates.
def administration_access(request):
    membership = get_membership(request.user) if request.user.is_authenticated else None
    return {"can_access_administration": can_administer(request.user, membership)}
