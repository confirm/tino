'''REST endpoints for bucket CRUD operations.'''

from fastapi import APIRouter, Depends, HTTPException

from ..auth import get_current_user, resolve_role
from ..dependencies import get_bucket_service, require_global_admin, require_viewer
from ..models import BucketCreate, BucketInfo, BucketUpdate
from ..services.bucket import BucketService

router = APIRouter(prefix='/api/buckets', tags=['buckets'])


@router.get('')
async def list_buckets(
    user=Depends(get_current_user),
    svc: BucketService = Depends(get_bucket_service),
):
    '''List buckets the user has access to, with their resolved role.'''
    results = []

    for bucket in svc.list():

        role = resolve_role(user, bucket.access)

        if role is not None:
            info         = bucket.model_dump()
            info['role'] = role
            results.append(info)

    return results


@router.get('/{slug}', response_model=BucketInfo)
async def get_bucket(slug: str, _user=Depends(require_viewer),
                     svc: BucketService = Depends(get_bucket_service)):
    '''Get metadata for a single bucket.'''
    bucket = svc.get(slug)

    if not bucket:
        raise HTTPException(404, 'Bucket not found')

    return bucket


@router.post('', response_model=BucketInfo, status_code=201)
async def create_bucket(
    body: BucketCreate,
    _user=Depends(require_global_admin),
    svc: BucketService = Depends(get_bucket_service),
):
    '''Create a new bucket (initializes a git repo with .meta.yml).'''
    try:
        return svc.create(body.slug, body.description, body.access)
    except FileExistsError as exc:
        raise HTTPException(409, 'Bucket already exists') from exc


@router.put('/{slug}', response_model=BucketInfo)
async def update_bucket(
    slug: str, body: BucketUpdate,
    _user=Depends(require_global_admin),
    svc: BucketService = Depends(get_bucket_service),
):
    '''Update a bucket's description or access rules.'''
    bucket = svc.update(slug, body.description, body.access)

    if not bucket:
        raise HTTPException(404, 'Bucket not found')

    return bucket


@router.delete('/{slug}', status_code=204)
async def delete_bucket(
    slug: str,
    _user=Depends(require_global_admin),
    svc: BucketService = Depends(get_bucket_service),
):
    '''Delete a bucket and its git repo from disk.'''
    if not svc.delete(slug):
        raise HTTPException(404, 'Bucket not found')
