"""
StarStream-Loro - Loro CRDT integration for StarStream

Conflict-free collaborative editing using Loro CRDTs.

Example:
    from starstream import StarStreamPlugin
    from starstream_loro import LoroPlugin

    app, rt = star_app()
    stream = StarStreamPlugin(app)
    loro = LoroPlugin(stream)

    @rt("/doc/{doc_id}")
    async def collaborative_doc(doc_id: str):
        # Automatic CRDT sync across all clients!
        return Editor(doc_id=doc_id)
"""

from .sync import LoroSyncManager
from .storage import LoroStorage
from .plugin import LoroPlugin

__version__ = "0.1.0"
__all__ = ["LoroSyncManager", "LoroStorage", "LoroPlugin"]
