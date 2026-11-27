'''WebSocket endpoint for real-time collaborative editing via Yjs CRDT.'''

import logging

from fastapi import APIRouter, Depends, HTTPException, WebSocket

from ..auth import check_access, get_current_user
from ..dependencies import get_bucket_service, get_collab_manager
from ..models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/buckets/{slug}', tags=['collab'])


@router.websocket('/collab/{path:path}')
async def collab_websocket(
    websocket: WebSocket,
    slug: str,
    path: str,
    user: User = Depends(get_current_user)
):
    '''Yjs WebSocket endpoint for real-time collaborative editing of a file.'''
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
    logger.info('Collab session started: %s/%s (user: %s)', slug, path, user.username)
    await collab.serve(websocket, slug, path)
    logger.info('Collab session ended: %s/%s (user: %s)', slug, path, user.username)
