"""Test isolation: force a throwaway SQLite DB and temp media dir before the
app package (and its settings/engine/storage singletons) are imported.
"""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="ascent-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["MEDIA_ROOT"] = os.path.join(_tmp, "media")

from app.database import Base, engine  # noqa: E402
import app.models  # noqa: E402,F401  (register tables on Base.metadata)

Base.metadata.create_all(engine)
