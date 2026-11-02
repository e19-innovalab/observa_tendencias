"""Create an observatory account from the command line (for the first administrator).

    python -m app.jobs.create_user --email ana@ejemplo.org --name "Ana Pérez" --role admin

The password is asked for interactively (or read from --password for scripts).
"""
import argparse
import getpass
import sys

from fastapi import HTTPException

from app.core.config_files import app_config
from app.core.database import SessionLocal
from app.services.users import create_user


def main() -> int:
    roles = list(app_config().auth.roles)
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", choices=roles, default=app_config().auth.default_role)
    parser.add_argument("--sector", default=None, help="sector de interés (código del catálogo)")
    parser.add_argument("--countries", default="", help="ISO3 separados por coma; vacío = región")
    parser.add_argument("--password", default=None)
    args = parser.parse_args()
    password = args.password or getpass.getpass("Contraseña: ")
    countries = [c for c in args.countries.split(",") if c.strip()]
    with SessionLocal() as session:
        try:
            user = create_user(session, args.email, args.name, password, args.role, args.sector,
                               countries)
        except HTTPException as exc:
            print(exc.detail)
            return 1
        session.commit()
        print(f"Usuario creado: {user.email} · rol {user.role} · id {user.user_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
