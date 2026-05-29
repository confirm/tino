'''REST endpoints for compiling Typst files to SVG or PDF.'''

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from ..collab import CollabManager
from ..dependencies import get_collab_manager, get_compiler_service, require_viewer
from ..services.compiler import CompilerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/buckets/{slug}/compile', tags=['compile'])


@router.get('/pdf/{path:path}')
async def compile_pdf(
    slug: str, path: str,
    _user=Depends(require_viewer),
    svc: CompilerService = Depends(get_compiler_service),
):
    '''Compile a .typ file and return the PDF.'''
    try:
        pdf_path = svc.compile_pdf(slug, path)
        filename = path.rsplit('/', maxsplit=1)[-1].replace('.typ', '.pdf')

        return FileResponse(
            pdf_path,
            filename=filename,
            media_type='application/pdf',
            background=BackgroundTask(pdf_path.unlink, missing_ok=True),
        )

    except FileNotFoundError as exc:
        raise HTTPException(404, 'File not found') from exc

    except RuntimeError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get('/svg/{path:path}')
async def compile_svg(
    slug: str, path: str,
    _user=Depends(require_viewer),
    svc: CompilerService = Depends(get_compiler_service),
):
    '''Compile a .typ file and return a list of SVG strings (one per page).'''
    try:
        pages = svc.compile_svg(slug, path)
        return {'pages': pages}

    except FileNotFoundError as exc:
        raise HTTPException(404, 'File not found') from exc

    except RuntimeError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get('/svg-live/{path:path}')
async def compile_svg_live(
    slug: str, path: str,
    user=Depends(require_viewer),
    svc: CompilerService = Depends(get_compiler_service),
    collab: CollabManager = Depends(get_collab_manager),
):
    '''Compile live editor content from the Yjs room, falling back to disk.'''
    try:
        content = collab.get_content(slug, path)

        if content is not None:  # pylint: disable=consider-ternary-expression
            logger.debug(
                'Live preview for %s/%s using collab content (user: %s)',
                slug, path, user.username,
            )
            pages = svc.compile_svg_from_content(slug, path, content)
        else:
            logger.debug(
                'Live preview for %s/%s falling back to disk (user: %s)',
                slug, path, user.username,
            )
            pages = svc.compile_svg(slug, path)

        return {'pages': pages}

    except FileNotFoundError as exc:
        raise HTTPException(404, 'File not found') from exc

    except RuntimeError as exc:
        raise HTTPException(422, str(exc)) from exc
