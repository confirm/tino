'''Pydantic models for API request/response schemas.'''

from typing import Annotated

from pydantic import BaseModel, Field

# ── Auth ──


class User(BaseModel):
    '''Authenticated user with group memberships.'''
    username: str
    email: str
    groups: list[str]
    api_key_access: dict[str, str] | None = None
    '''Per-bucket role map for API key authenticated requests (``None`` for OIDC users).'''


# ── Buckets ──


class AccessEntry(BaseModel):
    '''Maps a Keycloak group to a role within a bucket.'''
    group: str
    role: str  # viewer | editor


Slug = Annotated[str, Field(pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$', min_length=1, max_length=64)]


class BucketCreate(BaseModel):
    '''Request body for creating a new bucket.'''
    slug: Slug
    description: str = ''
    access: list[AccessEntry] = []


class BucketUpdate(BaseModel):
    '''Request body for updating bucket metadata. Omitted fields are unchanged.'''
    description: str | None = None
    access: list[AccessEntry] | None = None


class BucketInfo(BaseModel):
    '''Bucket metadata returned by the API.'''
    slug: str
    description: str
    created: str | None
    access: list[AccessEntry]


# ── Files ──


class FileCreate(BaseModel):
    '''Request body for creating a new file in a bucket.'''
    path: str
    content: str = ''


class FileSave(BaseModel):
    '''Request body for saving file content.'''
    content: str


class FileEntry(BaseModel):
    '''Single entry in a file listing.'''
    path: str
    type: str  # file | directory


# ── Git ──


class CommitRequest(BaseModel):
    '''Request body for committing selected files.'''
    files: list[str]
    message: str


class CommitInfo(BaseModel):
    '''Metadata for a single git commit.'''
    sha: str
    message: str
    author: str
    timestamp: str
    deleted: bool = False


class FileStatus(BaseModel):
    '''Git status of a single file in the working tree.'''
    path: str
    status: str  # modified | untracked | deleted


class DiffEntry(BaseModel):
    '''Unified diff output for a single file.'''
    path: str
    diff: str


class RestoreRequest(BaseModel):
    '''Request body for restoring files from a specific commit.'''
    ref: str
    paths: list[str]


# ── Templates ──


class TemplateInit(BaseModel):
    '''Request body for initializing a bucket from a Typst template.'''
    name: str
    namespace: str = 'preview'
    version: str
    target_dir: str = ''


# ── API Keys ──


class ApiKeyInfo(BaseModel):
    '''API key metadata returned by the API (no raw token or hash).'''
    id: str
    label: str
    created: str
    access: dict[str, str]


class ApiKeyCreate(BaseModel):
    '''Request body for creating or updating an API key.'''
    label: str
    access: dict[str, str] = {}


class ApiKeyCreated(BaseModel):
    '''Response when an API key is first created — includes the raw token (shown once only).'''
    token: str
    id: str
    label: str
    created: str
    access: dict[str, str]


# ── Fonts ──


class FontEntry(BaseModel):
    '''Metadata for an installed font file.'''
    filename: str
    size: int
