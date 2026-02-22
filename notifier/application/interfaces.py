import abc
import typing

from notifier.domain.entities import Issue, PullRequest


class Github(typing.Protocol):
    @abc.abstractmethod
    def get_issue(self) -> Issue: ...

    @abc.abstractmethod
    def get_pull_request(self) -> PullRequest: ...


class Notifier(typing.Protocol):
    @abc.abstractmethod
    def send_issue(
            self,
            issue: Issue,
            formatted_body: str,
            formatted_labels: str,
    ) -> None: ...

    @abc.abstractmethod
    def send_pull_request(
            self,
            pull_request: PullRequest,
            formatted_body: str,
            formatted_labels: str,
    ) -> None: ...


class MessageContext(typing.Protocol):
    @abc.abstractmethod
    def build(self, body: str) -> str:
        """Build a message with the given body."""
        ...

    @abc.abstractmethod
    def measure(self, message: str) -> int:
        """Get the length of the rendered message."""
        ...


class MessageLimiter(typing.Protocol):
    @abc.abstractmethod
    def truncate(self, context: MessageContext, body: str, limit: int) -> str:
        """Truncate the given body to fit within the given limit."""
        ...
