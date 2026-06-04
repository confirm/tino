'''REST endpoints for managing global API keys.'''

import logging

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import get_api_keys_service, require_global_admin
from ..models import ApiKeyCreate, ApiKeyCreated, ApiKeyInfo
from ..services.api_keys import ApiKeyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/keys', tags=['api-keys'])


@router.get('', response_model=list[ApiKeyInfo])
async def list_keys(
    user=Depends(require_global_admin),
    svc: ApiKeyService = Depends(get_api_keys_service),
):
    '''List all API keys (metadata only — tokens are never returned after creation).'''
    logger.debug('Listing API keys (user: %s)', user.username)
    return svc.list_keys()


@router.post('', response_model=ApiKeyCreated, status_code=201)
async def create_key(
    body: ApiKeyCreate,
    user=Depends(require_global_admin),
    svc: ApiKeyService = Depends(get_api_keys_service),
):
    '''Create a new API key.

    The raw token is returned **once** in the response and never stored.
    Store it securely — it cannot be retrieved again.
    '''
    raw, record = svc.create(body.label, body.access)
    logger.info('API key created: %s (%s) (user: %s)', record['id'], body.label, user.username)
    return ApiKeyCreated(token=raw, **record)


@router.patch('/{key_id}', response_model=ApiKeyInfo)
async def update_key(
    key_id: str,
    body: ApiKeyCreate,
    user=Depends(require_global_admin),
    svc: ApiKeyService = Depends(get_api_keys_service),
):
    '''Update the label and/or access map of an existing API key.'''
    result = svc.update(key_id, body.label, body.access)
    if result is None:
        raise HTTPException(404, 'API key not found')
    logger.info('API key updated: %s (user: %s)', key_id, user.username)
    return result


@router.delete('/{key_id}', status_code=204)
async def revoke_key(
    key_id: str,
    user=Depends(require_global_admin),
    svc: ApiKeyService = Depends(get_api_keys_service),
):
    '''Revoke (permanently delete) an API key.'''
    if not svc.revoke(key_id):
        raise HTTPException(404, 'API key not found')
    logger.info('API key revoked: %s (user: %s)', key_id, user.username)
