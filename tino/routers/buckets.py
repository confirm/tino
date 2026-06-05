'''REST endpoints for bucket CRUD operations.'''

import logging

from fastapi import APIRouter, Depends, HTTPException

from ..auth import get_current_user, resolve_role
from ..dependencies import get_bucket_service, require_global_admin, require_viewer
from ..models import BucketCreate, BucketInfo, BucketUpdate
from ..services.bucket import BucketService

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/buckets', tags=['buckets'])


@router.get('')
async def list_buckets(
    user=Depends(get_current_user),
    svc: BucketService = Depends(get_bucket_service),
):
    '''List buckets the user has access to, with their resolved role.'''
    results = []

    for bucket in svc.list():

        role = resolve_role(user, bucket.access, bucket.slug)

        if role is not None:
            info         = bucket.model_dump()
            info['role'] = role
            results.append(info)

    return results


@router.get('/{slug}', response_model=BucketInfo)
async def get_bucket(slug: str, user=Depends(require_viewer),
                     svc: BucketService = Depends(get_bucket_service)):
    '''Get metadata for a single bucket.'''
    logger.debug('Getting bucket %s (user: %s)', slug, user.username)
    bucket = svc.get(slug)

    if not bucket:
        raise HTTPException(404, 'Bucket not found')

    return bucket


@router.post('', response_model=BucketInfo, status_code=201)
async def create_bucket(
    body: BucketCreate,
    user=Depends(require_global_admin),
    svc: BucketService = Depends(get_bucket_service),
):
    '''Create a new bucket (initializes a git repo with .meta.yml).'''
    try:
        result = svc.create(
            body.slug, body.description, body.access,
            mcp_instructions=body.mcp_instructions, user=user,
        )
        logger.info('Bucket created: %s (user: %s)', body.slug, user.username)
        return result
    except FileExistsError as exc:
        logger.warning(
            'Bucket creation rejected: %s already exists (user: %s)',
            body.slug, user.username,
        )
        raise HTTPException(409, 'Bucket already exists') from exc


@router.put('/{slug}', response_model=BucketInfo)
async def update_bucket(
    slug: str, body: BucketUpdate,
    user=Depends(require_global_admin),
    svc: BucketService = Depends(get_bucket_service),
):
    '''Update a bucket's description or access rules.'''
    bucket = svc.update(
        slug, body.description, body.access,
        mcp_instructions=body.mcp_instructions, user=user,
    )

    if not bucket:
        logger.warning('Bucket update rejected: %s not found (user: %s)', slug, user.username)
        raise HTTPException(404, 'Bucket not found')

    logger.info('Bucket updated: %s (user: %s)', slug, user.username)
    return bucket


@router.delete('/{slug}', status_code=204)
async def delete_bucket(
    slug: str,
    user=Depends(require_global_admin),
    svc: BucketService = Depends(get_bucket_service),
):
    '''Delete a bucket and its git repo from disk.'''
    if not svc.delete(slug):
        logger.warning('Bucket deletion rejected: %s not found (user: %s)', slug, user.username)
        raise HTTPException(404, 'Bucket not found')

    logger.info('Bucket deleted: %s (user: %s)', slug, user.username)
