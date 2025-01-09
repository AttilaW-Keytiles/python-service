
AUTH_ROLE_EMPLOYEE: str = "employee"
"""A specific role - someone is an employee of the bank"""

AUTH_ROLES: dict[str, str] = {
    AUTH_ROLE_EMPLOYEE: "An employee of the Bank - has full authority over everything"
}
"""
Listing all available and valid Auth roles. Format: "role name" => "description of the role"
"""

