'''Dependency injection factories for FastAPI. Each factory is a singleton via @lru_cache.'''

from functools import lru_cache

from fastapi import Depends, HTTPException

from . import config
from .auth import check_access, get_current_user, is_global_admin
from .collab import CollabManager
from .models import User
from .notifier import BucketNotifier
from .services.bucket import BucketService
from .services.compiler import CompilerService
from .services.file import FileService
from .services.font import FontService
from .services.git import GitService
from .services.template import TemplateService


def _require_role(min_role: str):
    '''Create a dependency that checks the user has at least ``min_role`` on a bucket.'''
    def dependency(
        slug: str,
        user: User = Depends(get_current_user),
        svc: BucketService = Depends(get_bucket_service),
    ) -> User:
        bucket = svc.get(slug)

        if not bucket:
            raise HTTPException(404, 'Bucket not found')

        check_access(user, bucket.access, min_role)
        return user

    return dependency


def require_global_admin(user: User = Depends(get_current_user)) -> User:
    '''Require the user to be a global Typarr administrator.'''
    if not is_global_admin(user):
        raise HTTPException(403, 'Global admin role required')

    return user


@lru_cache
def get_file_service() -> FileService:
    '''Singleton FileService bound to the configured bucket directory.'''
    return FileService(config.TYPARR_BUCKET_DIR)


@lru_cache
def get_bucket_service() -> BucketService:
    '''Singleton BucketService bound to the configured bucket directory.'''
    return BucketService(config.TYPARR_BUCKET_DIR)


@lru_cache
def get_git_service() -> GitService:
    '''Singleton GitService bound to the configured bucket directory.'''
    return GitService(config.TYPARR_BUCKET_DIR)


@lru_cache
def get_compiler_service() -> CompilerService:
    '''Singleton CompilerService bound to the configured bucket directory.'''
    return CompilerService(config.TYPARR_BUCKET_DIR, config.TYPARR_PACKAGE_DIR,
                           config.TYPARR_FONT_DIR)


@lru_cache
def get_template_service() -> TemplateService:
    '''Singleton TemplateService bound to the configured bucket directory.'''
    return TemplateService(config.TYPARR_BUCKET_DIR, config.TYPARR_PACKAGE_DIR)


@lru_cache
def get_font_service() -> FontService:
    '''Singleton FontService bound to the configured font directory.'''
    return FontService(config.TYPARR_FONT_DIR)


@lru_cache
def get_notifier() -> BucketNotifier:
    '''Singleton BucketNotifier for broadcasting file-change events.'''
    return BucketNotifier()


@lru_cache
def get_collab_manager() -> CollabManager:
    '''Singleton CollabManager wired to the FileService for disk flushing.'''
    return CollabManager(
        data_dir=config.TYPARR_BUCKET_DIR,
        file_service=get_file_service(),
        auto_save=config.TYPARR_SAVE_DEBOUNCE_MS > 0,
        room_ttl=config.TYPARR_ROOM_TTL,
    )


require_viewer    = _require_role('viewer')
require_editor    = _require_role('editor')
require_committer = _require_role('committer')
