'''REST endpoint for global search across the buckets a user can access.'''

import logging

from fastapi import APIRouter, Depends, HTTPException

from ..auth import get_current_user, resolve_role
from ..dependencies import get_bucket_service, get_search_service
from ..models import SearchResult, User
from ..services.bucket import BucketService
from ..services.search import SearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/search', tags=['search'])

#: Queries shorter than this are ignored (returns an empty list).
MIN_QUERY_LEN = 2

#: Maximum number of file results returned across all searched buckets.
MAX_RESULTS = 100


def _allowed_slugs(user: User, svc: BucketService, bucket: str | None) -> list[str]:
    '''Resolve which bucket slugs the user may search.

    With *bucket* set, restrict to that single bucket (404 if missing, 403 if the
    user has no access). Otherwise return every bucket the user can at least view.
    '''
    if bucket is not None:
        info = svc.get(bucket)
        if info is None:
            raise HTTPException(404, 'Bucket not found')
        if resolve_role(user, info.access, bucket) is None:
            raise HTTPException(403, 'You do not have access to this bucket')
        return [bucket]

    return [
        info.slug for info in svc.list()
        if resolve_role(user, info.access, info.slug) is not None
    ]


@router.get('', response_model=list[SearchResult])
async def search(
    q: str,
    bucket: str | None = None,
    user: User = Depends(get_current_user),
    bucket_svc: BucketService = Depends(get_bucket_service),
    search_svc: SearchService = Depends(get_search_service),
):
    '''Search file names and content across the buckets the user can access.

    Pass *bucket* to limit the search to a single bucket, or omit it to search
    every accessible bucket. Results are capped at :data:`MAX_RESULTS` files.
    '''
    query = q.strip()
    if len(query) < MIN_QUERY_LEN:
        return []

    slugs = _allowed_slugs(user, bucket_svc, bucket)
    logger.debug('Search %r over %d bucket(s) (user: %s)', query, len(slugs), user.username)

    results: list[SearchResult] = []
    for slug in slugs:
        remaining = MAX_RESULTS - len(results)
        if remaining <= 0:
            break
        results.extend(search_svc.search_bucket(slug, query, limit=remaining))

    return results
