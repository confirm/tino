'''REST endpoints for file CRUD within a bucket's working tree.'''

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.params import File
from fastapi.responses import FileResponse

from ..dependencies import get_file_service, require_editor, require_viewer
from ..models import FileCreate, FileEntry, FileSave
from ..services.file import FileService

router = APIRouter(prefix='/api/buckets/{slug}/files', tags=['files'])


@router.get('', response_model=list[FileEntry])
async def list_files(
    slug: str,
    _user=Depends(require_viewer),
    svc: FileService = Depends(get_file_service),
):
    '''List all files and directories in a bucket (excludes .git and .meta.yml).'''
    return svc.list(slug)


@router.get('/raw/{path:path}')
async def raw_file(
    slug: str, path: str,
    _user=Depends(require_viewer),
    svc: FileService = Depends(get_file_service),
):
    '''Serve a file's raw content (for images, binary previews, etc.).'''
    target = svc.resolve(slug, path)
    if target is None:
        raise HTTPException(404, 'File not found')
    return FileResponse(target)


@router.get('/{path:path}')
async def read_file(
    slug: str, path: str,
    _user=Depends(require_viewer),
    svc: FileService = Depends(get_file_service),
):
    '''Read a single file's content by path.'''
    result = svc.read(slug, path)
    if result is None:
        raise HTTPException(404, 'File not found')
    return {'path': path, **result}


@router.post('', status_code=201)
async def create_file(
    slug: str, body: FileCreate,
    _user=Depends(require_editor),
    svc: FileService = Depends(get_file_service),
):
    '''Create a new file in the bucket. Fails if the file already exists.'''
    if not svc.create(slug, body.path, body.content):
        raise HTTPException(409, 'File already exists or invalid path')
    return {'path': body.path}


@router.put('/{path:path}')
async def save_file(
    slug: str, path: str, body: FileSave,
    _user=Depends(require_editor),
    svc: FileService = Depends(get_file_service),
):
    '''Overwrite a file's content (used by manual save and auto-save).'''
    modified = svc.write(slug, path, body.content)
    if not modified:
        raise HTTPException(400, 'Invalid path')
    return {'path': path, 'modified': modified}


@router.post('/upload', status_code=201)
async def upload_files(
    slug: str,
    files: list[UploadFile] = File(...),
    prefix: str = '',
    _user=Depends(require_editor),
    svc: FileService = Depends(get_file_service),
):
    '''Upload one or more binary/text files via multipart form data.'''
    uploaded = []
    for file in files:
        path = f'{prefix}/{file.filename}' if prefix else file.filename
        data = await file.read()
        if not svc.upload(slug, path, data):
            raise HTTPException(400, f'Invalid path: {path}')
        uploaded.append(path)
    return {'uploaded': uploaded}


@router.post('/rename-dir')
async def rename_dir(
    slug: str, body: dict,
    _user=Depends(require_editor),
    svc: FileService = Depends(get_file_service),
):
    '''Rename/move a directory and all its contents.'''
    affected = svc.rename_dir(slug, body['old_path'], body['new_path'])
    if affected is None:
        raise HTTPException(400, 'Invalid path or target exists')
    return {'affected': affected}


@router.delete('/dir/{path:path}', status_code=204)
async def delete_dir(
    slug: str, path: str,
    _user=Depends(require_editor),
    svc: FileService = Depends(get_file_service),
):
    '''Delete a directory and all its contents.'''
    if svc.delete_dir(slug, path) is None:
        raise HTTPException(404, 'Directory not found')


@router.delete('/{path:path}', status_code=204)
async def delete_file(
    slug: str, path: str,
    _user=Depends(require_editor),
    svc: FileService = Depends(get_file_service),
):
    '''Delete a file from the bucket's working tree.'''
    if not svc.delete(slug, path):
        raise HTTPException(404, 'File not found')
