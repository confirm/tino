'''REST endpoints for browsing and initializing Typst templates.'''

import logging

from fastapi import APIRouter, Depends, HTTPException

from ..auth import get_current_user
from ..dependencies import get_template_service, require_editor
from ..models import TemplateInit
from ..services.template import TemplateService

logger = logging.getLogger(__name__)

router = APIRouter(tags=['templates'])


@router.get('/api/templates/typst-universe')
async def list_typst_universe_templates(
    _user=Depends(get_current_user),
    svc: TemplateService = Depends(get_template_service),
):
    '''Return all available Typst templates from the Typst Universe package index.'''
    return svc.list_typst_universe_templates()


@router.get('/api/templates/local')
async def list_local_templates(
    _user=Depends(get_current_user),
    svc: TemplateService = Depends(get_template_service),
):
    '''Return templates from the local package directory.'''
    return svc.list_local_templates()


@router.post('/api/buckets/{slug}/init-template')
async def init_template(
    slug: str, body: TemplateInit,
    user=Depends(require_editor),
    svc: TemplateService = Depends(get_template_service),
):
    '''Initialize a bucket from a Typst template via typst init.'''
    try:
        svc.init_template(
            slug, body.name, body.version, body.namespace,
        )
        return {'status': 'ok'}

    except FileNotFoundError as exc:
        logger.warning('Template init rejected for %s (user: %s): %s', slug, user.username, exc)
        raise HTTPException(404, str(exc)) from exc

    except FileExistsError as exc:
        logger.warning('Template init rejected for %s (user: %s): %s', slug, user.username, exc)
        raise HTTPException(409, str(exc)) from exc

    except RuntimeError as exc:
        logger.warning('Template init failed for %s (user: %s): %s', slug, user.username, exc)
        raise HTTPException(422, str(exc)) from exc
