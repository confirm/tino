'''REST endpoints for managing custom fonts (admin-only).'''

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.params import File

from ..dependencies import get_font_service, require_global_admin
from ..models import FontEntry
from ..services.font import FontService

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/fonts', tags=['fonts'])


@router.get('', response_model=list[FontEntry])
async def list_fonts(
    user=Depends(require_global_admin),
    svc: FontService = Depends(get_font_service),
):
    '''Return all installed custom fonts.'''
    logger.debug('Listing fonts (user: %s)', user.username)
    return svc.list()


@router.post('/upload', status_code=201)
async def upload_fonts(
    files: list[UploadFile] = File(...),
    user=Depends(require_global_admin),
    svc: FontService = Depends(get_font_service),
):
    '''Upload one or more font files (TTF, OTF, WOFF, WOFF2).'''
    uploaded = []
    for file in files:
        data = await file.read()
        if not svc.upload(file.filename, data):
            logger.warning(
                'Font upload rejected: invalid file %s (user: %s)',
                file.filename, user.username,
            )
            raise HTTPException(400, f'Invalid font file: {file.filename}')
        uploaded.append(file.filename)
    return {'uploaded': uploaded}


@router.delete('/{filename}', status_code=204)
async def delete_font(
    filename: str,
    user=Depends(require_global_admin),
    svc: FontService = Depends(get_font_service),
):
    '''Delete a font file.'''
    if not svc.delete(filename):
        logger.warning('Font deletion rejected: %s not found (user: %s)', filename, user.username)
        raise HTTPException(404, 'Font not found')
