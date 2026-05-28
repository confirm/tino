'''WebSocket endpoint for bucket-level file change notifications.'''

from fastapi import APIRouter, HTTPException, WebSocket

from ..auth import check_access
from ..dependencies import get_bucket_service, get_notifier
from ..models import User

router = APIRouter(prefix='/api/buckets/{slug}', tags=['events'])


@router.websocket('/events')
async def bucket_events(websocket: WebSocket, slug: str):
    '''Subscribe to file-change events for a bucket.'''
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
        check_access(user, bucket.access, 'viewer')
    except HTTPException:
        await websocket.close(code=4403, reason='Viewer role required')
        return

    notifier = get_notifier()
    await notifier.serve(websocket, slug)
