'''WebSocket endpoint for real-time collaborative editing via Yjs CRDT.'''

import logging

from fastapi import APIRouter, HTTPException, WebSocket

from ..auth import check_access
from ..dependencies import get_bucket_service, get_collab_manager
from ..models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/buckets/{slug}', tags=['collab'])


@router.websocket('/collab/{path:path}')
async def collab_websocket(websocket: WebSocket, slug: str, path: str):
    '''Yjs WebSocket endpoint for real-time collaborative editing of a file.'''
    user_data = websocket.session.get('user')
    if not user_data:
        await websocket.close(code=4401, reason='Not authenticated')
        return

    user   = User(**user_data)
    bucket = get_bucket_service().get(slug)

    if not bucket:
        await websocket.close(code=4004, reason='Bucket not found')
        return

    try:
        check_access(user, bucket.access, 'editor', slug)
    except HTTPException:
        await websocket.close(code=4403, reason='Editor role required')
        return

    collab = get_collab_manager()
    logger.info('Collab session started for %s/%s by %s', slug, path, user.username)
    await collab.serve(websocket, slug, path)
    logger.info('Collab session ended for %s/%s by %s', slug, path, user.username)
