"""Legacy deployment identifiers, retained solely to keep existing data reachable.

Display names and new settings use RAGFUSION. Renaming database roles or Redis
keys without a coordinated data migration would break credentials or reset quotas.
"""
import os
import re
from pathlib import Path

LEGACY_ENV_PREFIX = 'DOCPRO_'
LEGACY_DATABASE_URL = 'postgresql+asyncpg://docpro:docpro@localhost:5432/docpro'
LEGACY_UPLOAD_DIR = '/tmp/docpro_uploads'
RATE_LIMIT_NAMESPACE = 'docpro:rate'
JWT_ISSUER = 'docpro-v2'
JWT_AUDIENCE = 'docpro-api'


def environment_value(name: str, default=None):
    return os.getenv(name, os.getenv(name.replace('RAGFUSION_', LEGACY_ENV_PREFIX), default))


def default_upload_dir():
    return LEGACY_UPLOAD_DIR if Path(LEGACY_UPLOAD_DIR).exists() else '/tmp/ragfusion_uploads'


def display_brand(value: str):
    canonical = re.sub('docpro', 'RAGFUSION', value, flags=re.IGNORECASE)
    # V2 was a legacy display suffix. Keep protocol identifiers (JWT issuer,
    # model names, Redis namespace) untouched, but never expose the suffix in
    # user-facing application names.
    return re.sub(r'\s+v2\b', '', canonical, flags=re.IGNORECASE).strip()
