# Example: copy to an importable package and set
# PDD_GENERATOR_AUTH_PROVIDER_EXTENSIONS_MODULE=my_package.my_auth_plugins
#
# from collections.abc import Callable
# from app.services.auth.auth_types import IdentityProvider
#
# AUTH_PROVIDER_FACTORIES: dict[str, Callable[[], IdentityProvider]] = {
#     "my_oidc": lambda: MyOidcIdentityProvider(),
# }
