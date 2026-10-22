'''Pydantic models for API request/response schemas.'''

from typing import Annotated, Literal

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


Slug = Annotated[str, Field(pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$', min_length=1, max_length=50)]


class BucketCreate(BaseModel):
    '''Request body for creating a new bucket.'''
    slug: Slug
    name: str = Field('', max_length=50)
    description: str = ''
    access: list[AccessEntry] = []
    mcp_instructions: str = ''


class BucketUpdate(BaseModel):
    '''Request body for updating bucket metadata. Omitted fields are unchanged.'''
    name: str | None = Field(None, max_length=50)
    description: str | None = None
    access: list[AccessEntry] | None = None
    mcp_instructions: str | None = None


class BucketInfo(BaseModel):
    '''Bucket metadata returned by the API.'''
    slug: str
    name: str = ''
    description: str
    access: list[AccessEntry]
    mcp_instructions: str = ''


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


# ── Search ──


class SearchSnippet(BaseModel):
    '''A single content line that matched a search query.'''
    line: int
    text: str


class SearchResult(BaseModel):
    '''A file whose name and/or content matched a search query.'''
    bucket: str
    path: str
    name_match: bool = False
    snippets: list[SearchSnippet] = []


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


# ── Review comments ──


class ReviewAnchor(BaseModel):
    '''Source range a review thread is attached to.'''
    from_offset: int = Field(ge=0)
    to_offset: int = Field(ge=0)
    line: int = Field(ge=1)
    column: int = Field(ge=1)
    end_line: int = Field(ge=1)
    end_column: int = Field(ge=1)
    quote: str = ''


class ReviewMessage(BaseModel):
    '''A single message in a review thread.'''
    id: str
    author: str
    created_at: str
    body: str


class ReviewThread(BaseModel):
    '''A source-anchored review thread.'''
    id: str
    path: str
    anchor: ReviewAnchor
    status: Literal['open', 'resolved'] = 'open'
    created_by: str
    created_at: str
    resolved_by: str | None = None
    resolved_at: str | None = None
    messages: list[ReviewMessage]


class ReviewThreadCreate(BaseModel):
    '''Request body for creating a review thread.'''
    path: str
    anchor: ReviewAnchor
    body: str = Field(min_length=1)


class ReviewReplyCreate(BaseModel):
    '''Request body for replying to a review thread.'''
    body: str = Field(min_length=1)


class ReviewThreadUpdate(BaseModel):
    '''Request body for changing review thread state.'''
    status: Literal['open', 'resolved']


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
