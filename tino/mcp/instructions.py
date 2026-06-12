'''Server-level MCP instructions, shared by the MCP server and the REST API.

Kept free of the MCP SDK so the bucket settings dialog can fetch the full
instruction text (built-in plus the ``TINO_MCP_INSTRUCTIONS`` override) without
pulling in the MCP server machinery.
'''

from .. import config

#: Built-in instructions describing TINO and how an agent should use the tools.
BASE_INSTRUCTIONS = '''\
TINO is a collaborative Typst document platform.
Documents live in *buckets* (git repositories).
Use these tools to list, read, write, compile, and commit Typst source files.
Always compile after editing to verify the document is valid.
Each bucket may have specific instructions.
Always list buckets first and follow any per-bucket guidance.
To locate a document by file name or content, use the ``search`` tool instead of
listing and reading every file.
'''


def server_instructions() -> str:
    '''Return the full server-level instructions an MCP agent receives.

    This is :data:`BASE_INSTRUCTIONS` plus the optional
    :attr:`~tino.config.TINO_MCP_INSTRUCTIONS` global override.  Per-bucket
    instructions are appended separately (see the ``list_buckets`` tool).
    '''
    text = BASE_INSTRUCTIONS
    if config.TINO_MCP_INSTRUCTIONS:
        text += '\n' + config.TINO_MCP_INSTRUCTIONS + '\n'
    return text
