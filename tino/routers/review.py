'''REST endpoints for source-anchored review comments.'''

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from ..dependencies import get_review_service, require_editor, require_viewer
from ..models import ReviewReplyCreate, ReviewThread, ReviewThreadCreate, ReviewThreadUpdate
from ..services.review import ReviewPathError, ReviewService, ReviewThreadNotFound

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/buckets/{slug}/comments', tags=['comments'])


@router.get('', response_model=list[ReviewThread])
async def list_comments(
    slug: str,
    user=Depends(require_viewer),
    svc: ReviewService = Depends(get_review_service),
    path: str | None = Query(None),
    status: str = Query('open', pattern='^(open|resolved|all)$'),
):
    '''List review threads in a bucket, optionally filtered by file path and status.'''
    logger.debug('Listing review comments for %s/%s (user: %s)', slug, path, user.username)
    return svc.list(slug, path, status)


@router.post('', response_model=ReviewThread, status_code=201)
async def create_comment(
    slug: str,
    body: ReviewThreadCreate,
    user=Depends(require_editor),
    svc: ReviewService = Depends(get_review_service),
):
    '''Create a review thread anchored to a source range.'''
    try:
        return svc.create(slug, body, user)
    except ReviewPathError as exc:
        logger.warning(
            'Comment creation rejected for %s/%s (user: %s)',
            slug, body.path, user.username,
        )
        raise HTTPException(400, 'Invalid comment path') from exc


@router.post('/{thread_id}/replies', response_model=ReviewThread)
async def reply_to_comment(
    slug: str,
    thread_id: str,
    body: ReviewReplyCreate,
    user=Depends(require_editor),
    svc: ReviewService = Depends(get_review_service),
):
    '''Append a reply to an existing review thread.'''
    try:
        return svc.reply(slug, thread_id, body, user)
    except ReviewThreadNotFound as exc:
        logger.warning('Reply rejected for missing review thread %s in %s', thread_id, slug)
        raise HTTPException(404, 'Comment not found') from exc


@router.patch('/{thread_id}', response_model=ReviewThread)
async def update_comment(
    slug: str,
    thread_id: str,
    body: ReviewThreadUpdate,
    user=Depends(require_editor),
    svc: ReviewService = Depends(get_review_service),
):
    '''Resolve or reopen a review thread.'''
    try:
        return svc.update(slug, thread_id, body, user)
    except ReviewThreadNotFound as exc:
        logger.warning('Update rejected for missing review thread %s in %s', thread_id, slug)
        raise HTTPException(404, 'Comment not found') from exc
