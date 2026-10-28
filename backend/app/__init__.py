"""RAGFUSION backend application package."""

import os

# Apply before any lazy parser import, including native (non-Docker) launches.
os.environ.setdefault("UNSTRUCTURED_DISABLE_NOTICE", "1")
