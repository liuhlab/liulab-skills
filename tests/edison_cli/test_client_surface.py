"""What the installed `edison-client` actually offers, checked against what this package calls.

Every other test here answers with a stub, which proves the CLI's own behaviour and nothing
about the package it drives. This one reads the real client — importing it opens no socket —
so that a lock that quietly moved `edison-client` somewhere else is a red test rather than a
failure the first time someone spends a credit.

It is the guard the repo did not have when a solve resolved 0.11.1: that build installs
cleanly, reports a plausible version, and cannot be imported at all.
"""

from __future__ import annotations

import importlib.metadata
import inspect

import pytest

from edison_cli import tasks

# Importing the real client takes seconds, and each test process pays it once. One group
# keeps this file on one worker (`--dist loadgroup` in the `test` task), so one worker pays.
pytestmark = pytest.mark.xdist_group("real-edison-client")

CALLED = {
    "create_task": ("task_data", "files"),
    "get_task": ("task_id", "lite"),
    "get_tasks": ("project_id", "limit"),
    "cancel_task": ("task_id",),
    "list_files": ("trajectory_id",),
    "fetch_data_from_storage": ("data_storage_id",),
    "create_project": ("name", "description", "persona_id"),
    "list_persona_owned_projects": ("persona_id", "limit"),
    "add_task_to_project": ("project_id", "trajectory_id"),
    "send_chat_message": ("project_id", "message", "job_name", "data_storage_ids"),
    "queue_chat_message": ("session_id", "project_id", "message"),
    "get_conversation": ("session_id", "limit"),
    "get_conversations": ("limit",),
    "get_session": ("session_id",),
    "upload_file": ("file_path", "name", "description"),
    "store_file_content": ("name", "file_path", "as_collection", "ignore_patterns"),
    "search_data_storage": ("text_query", "limit"),
}


def test_the_locked_client_is_the_one_the_reference_pages_were_read_from() -> None:
    """Below 0.16 the reference pages describe a package that is not installed."""
    version = importlib.metadata.version("edison-client")
    major, minor = (int(part) for part in version.split(".")[:2])
    assert (major, minor) >= (0, 16), f"edison-client {version} predates every recorded fact"


def test_the_client_imports_at_all() -> None:
    """A solve can install `edison-client` and a `fhlmi` that makes importing it raise."""
    from edison_client import EdisonClient

    assert callable(EdisonClient)


@pytest.mark.parametrize(("method", "arguments"), sorted(CALLED.items()))
def test_every_method_this_package_calls_exists_with_the_arguments_it_passes(
    method: str, arguments: tuple[str, ...]
) -> None:
    """A renamed keyword is a runtime failure on the spending path; here it is a red test."""
    from edison_client import EdisonClient

    function = getattr(EdisonClient, method, None)
    assert function is not None, f"edison-client no longer has {method}"
    parameters = inspect.signature(function).parameters
    for name in arguments:
        assert name in parameters, f"{method} no longer takes {name}"


def test_a_conversation_message_still_carries_what_was_attached_to_it() -> None:
    """`kosmos status` reads the platform's record of the attachment out of `info`.

    Nothing else on this surface says whether an attachment survived the send. If the field
    went away, `status` would print nothing — and a run whose attachment was dropped looks
    exactly like a run that was started without one.
    """
    from edison_client.models.chat import ConversationMessage

    assert "info" in ConversationMessage.model_fields


def test_the_authenticated_http_client_is_still_reachable_under_the_client() -> None:
    """Personas have no client method at all, so `.client` is the only route to them."""
    from edison_client import EdisonClient

    assert isinstance(EdisonClient.client, property)


def test_every_job_this_package_will_send_is_a_real_member() -> None:
    """The allow-list is what turns "never guess a job name" into something unguessable."""
    from edison_client.models.app import JobNames

    for job in tasks.JOBS:
        assert job in JobNames.__members__


@pytest.mark.parametrize("member", sorted(tasks.NOT_SENT))
def test_a_member_that_404s_is_a_real_member_and_still_off_the_allow_list(member: str) -> None:
    """PHOENIX and DUMMY are in the enum and both 404 on a new submission, which is the trap.

    Both halves matter. If the member vanished from the enum the entry would be describing a
    name nobody can type; if it reappeared on the allow-list a submission would buy a 404.
    """
    from edison_client.models.app import JobNames

    assert member in JobNames.__members__
    assert member not in tasks.JOBS


@pytest.mark.parametrize("member", sorted(tasks.NOT_SENT))
def test_the_refusal_says_the_member_is_real_rather_than_unknown(member: str) -> None:
    """Calling it unknown is untrue of a member in the enum, and sends the reader hunting."""
    from edison_cli.runtime import Refusal

    with pytest.raises(Refusal) as raised:
        tasks.check_job(member)
    assert "real JobNames member" in str(raised.value)
    assert "unknown job" not in str(raised.value)


def test_a_name_that_is_in_no_enum_at_all_is_still_refused_as_unknown() -> None:
    """The allow-list's first job is the invented string, and that refusal must not change."""
    from edison_cli.runtime import Refusal

    with pytest.raises(Refusal) as raised:
        tasks.check_job("SPARROW")
    assert "never invent a name" in str(raised.value)


def test_two_unrelated_exception_trees_are_both_called_rest_client_error() -> None:
    """`except RestClientError` catches one of them, which is why `sentence` catches neither.

    It reads the response off the exception instead, so a class this package never imported
    still comes out as a sentence.
    """
    from edison_client.clients import exceptions, rest_client

    assert exceptions.RestClientError is not rest_client.RestClientError
    assert not issubclass(rest_client.RestClientError, exceptions.RestClientError)


def test_a_client_failure_reads_as_a_sentence_rather_than_a_traceback() -> None:
    """The client re-raises a raw `httpx.HTTPStatusError` for every retryable status."""
    from edison_cli.runtime import sentence

    class Response:
        status_code = 500
        text = '{"detail": "something went wrong upstream"}'

    class RaisedError(Exception):
        response = Response()

    said = sentence(RaisedError())
    assert "500" in said
    assert "something went wrong upstream" in said
    assert "Traceback" not in said


def test_a_missing_id_is_reported_as_a_missing_id() -> None:
    """`cancel_task` looks the task up first, and that lookup is where the 404 escapes."""
    from edison_cli.runtime import sentence

    class Response:
        status_code = 404
        text = ""

    class RaisedError(Exception):
        response = Response()

    assert "404" in sentence(RaisedError())
    assert "no record of that id" in sentence(RaisedError())


def test_a_404_on_a_call_that_carried_no_id_says_so_instead() -> None:
    """A submission hands the platform no id, so "find it again with `task list`" is nonsense."""
    from edison_cli.runtime import sentence

    class Response:
        status_code = 404
        text = ""

    class RaisedError(Exception):
        response = Response()

    said = sentence(RaisedError(), not_found=tasks.SUBMIT_404)
    assert "404" in said
    assert "nothing was created" in said
    assert "task list" not in said
