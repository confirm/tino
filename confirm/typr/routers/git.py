'''REST endpoints for git operations on a bucket's repository.'''

from fastapi import APIRouter, Depends, HTTPException, Query

from ..dependencies import get_git_service, require_committer, require_viewer
from ..models import CommitInfo, CommitRequest, DiffEntry, FileStatus, RestoreRequest
from ..services.git import GitService

router = APIRouter(prefix='/api/buckets/{slug}/git', tags=['git'])


@router.get('/status', response_model=list[FileStatus])
async def git_status(
    slug: str,
    _user=Depends(require_viewer),
    svc: GitService = Depends(get_git_service),
):
    '''Return per-file working tree status (modified, untracked, deleted, staged).'''
    try:
        return svc.status(slug)
    except Exception as exc:
        raise HTTPException(404, 'Bucket not found or not a git repo') from exc


@router.post('/commit', response_model=CommitInfo)
async def git_commit(
    slug: str, body: CommitRequest,
    user=Depends(require_committer),
    svc: GitService = Depends(get_git_service),
):
    '''Stage the selected files and create a new commit.'''
    if not body.files:
        raise HTTPException(400, 'No files specified')
    try:
        return svc.commit(slug, body.files, body.message, author=user.username, email=user.email)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get('/log', response_model=list[CommitInfo])
async def git_log(
    slug: str,
    _user=Depends(require_viewer),
    svc: GitService = Depends(get_git_service),
    path: str | None = Query(None),
    max_count: int = Query(50, ge=1, le=500),
):
    '''Return commit history, optionally filtered to a single file path.'''
    try:
        return svc.log(slug, path, max_count=max_count)
    except Exception as exc:
        raise HTTPException(404, 'Bucket not found') from exc


@router.get('/diff', response_model=list[DiffEntry])
async def git_diff(
    slug: str,
    _user=Depends(require_viewer),
    svc: GitService = Depends(get_git_service),
    path: str | None = Query(None),
):
    '''Return unified diffs for modified files in the working tree.'''
    try:
        return svc.diff(slug, path)
    except Exception as exc:
        raise HTTPException(404, 'Bucket not found') from exc


@router.get('/tree/{ref}')
async def git_tree(
    slug: str, ref: str,
    _user=Depends(require_viewer),
    svc: GitService = Depends(get_git_service),
):
    '''List all files at a specific commit ref.'''
    try:
        return svc.tree(slug, ref)
    except Exception as exc:
        raise HTTPException(404, 'Commit not found') from exc


@router.get('/show/{ref}/{path:path}')
async def git_show(
    slug: str, ref: str, path: str,
    _user=Depends(require_viewer),
    svc: GitService = Depends(get_git_service),
):
    '''Retrieve a file's content at a specific commit ref.'''
    content = svc.show(slug, ref, path)
    if content is None:
        raise HTTPException(404, 'File not found at that ref')
    return {'ref': ref, 'path': path, 'content': content}


@router.post('/restore')
async def git_restore(
    slug: str, body: RestoreRequest,
    _user=Depends(require_committer),
    svc: GitService = Depends(get_git_service),
):
    '''Restore file(s) from a specific commit into the working tree.'''
    restored = svc.restore(slug, body.ref, body.paths)
    if not restored:
        raise HTTPException(404, 'No files could be restored')
    return {'restored': restored}
