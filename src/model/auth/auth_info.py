
class AuthInfo:
    """
    Represents an authenicated entity.
    """

    def __init__(self, user_id: str, user_name: str, roles: set[str]):
        self.user_id = user_id
        """The user.id (from table) who this auth info represents"""
        self.user_name = user_name
        """The user.username (from table) who this auth info represents"""
        self.roles = roles
        if self.roles == None:
            self.roles = set()
        """Set of associated roles - basically what can this guy do? (details later - but see rolse.py!)"""

    def has_role(self, role: str) -> bool:
        """Checks if we have this role or not"""
        for role_has in self.roles:
            if role_has == role:
                return True
        return False
