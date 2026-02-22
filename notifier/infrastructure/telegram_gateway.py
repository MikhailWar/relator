import typing

import sulguk

from notifier.application import interfaces
from notifier.domain.entities import Issue, PullRequest
from notifier.infrastructure.send_weebhook import send_webhook

TG_MESSAGE_LIMIT: typing.Final = 4096

ISSUE_TEMPLATE: typing.Final = (
    "🚀 <b>New issue to <a href=/{repository}>{repository}</a> by <a href=/{user}>@{user}</a> </b><br/>"
    "📝 <b>{title}</b> (<a href='{url}'>#{id}</a>)<br/><br/>"
    "{body}<br/>"
    "{labels}"
    "{promo}"
)

PR_TEMPLATE: typing.Final = (
    "🎉 <b>New Pull Request to <a href=/{repository}>{repository}</a> by <a href=/{user}>@{user}</a></b><br/>"
    "✨ <b>{title}</b> (<a href='{url}'>#{id}</a>)<br/>"
    "📊 +{additions}/-{deletions}<br/>"
    "🌿 {head_ref} → {base_ref}<br/><br/>"
    "{body}<br/>"
    "{labels}"
    "{promo}"
)


class TelegramMessageContext(interfaces.MessageContext):
    def __init__(
        self,
        build_message: typing.Callable[[typing.Any, str, str], str],
        entity: typing.Any,
        labels: str,
    ) -> None:
        self._build_message = build_message
        self._entity = entity
        self._labels = labels

    def build(self, body: str) -> str:
        return self._build_message(self._entity, body, self._labels)

    def measure(self, message: str) -> int:
        render = sulguk.transform_html(message, base_url="https://github.com")
        return len(render.text)


class TelegramGateway(interfaces.Notifier):
    def __init__(
        self,
        chat_id: str,
        bot_token: str,
        attempt_count: int,
        message_limiter: interfaces.MessageLimiter,
        message_thread_id: str | int | None = None,
        custom_template: str = "",
        tg_message_limit: int = TG_MESSAGE_LIMIT,

    ) -> None:
        self._chat_id = chat_id
        self._bot_token = bot_token
        self._attempt_count = attempt_count
        self._message_thread_id = message_thread_id
        self._custom_template = custom_template
        self._message_limiter = message_limiter
        self._tg_message_limit = tg_message_limit

    def send_issue(
        self,
        issue: Issue,
        formatted_body: str,
        formatted_labels: str,
    ) -> None:
        message = self._create_issue_message(issue, formatted_body, formatted_labels)
        render_result = sulguk.transform_html(message, base_url="https://github.com")

        if len(render_result.text) > self._tg_message_limit:
            context = TelegramMessageContext(
                build_message=self._create_issue_message,
                entity=issue,
                labels=formatted_labels,
            )
            truncated_body = self._message_limiter.truncate(
                context=context,
                body=formatted_body,
                limit=self._tg_message_limit,
            )
            message = self._create_issue_message(
                issue, truncated_body, formatted_labels
            )
            render_result = sulguk.transform_html(
                message, base_url="https://github.com"
            )
        send_webhook(
            payload=self._create_payload(render_result),
            url=f"https://api.telegram.org/bot{self._bot_token}/sendMessage",
            attempts=self._attempt_count,
        )

    def send_pull_request(
        self,
        pull_request: PullRequest,
        formatted_body: str,
        formatted_labels: str,
    ) -> None:
        message = self._create_pr_message(
            pull_request, formatted_body, formatted_labels
        )
        render_result = sulguk.transform_html(message, base_url="https://github.com")

        if len(render_result.text) > self._tg_message_limit:
            context = TelegramMessageContext(
                build_message=self._create_pr_message,
                entity=pull_request,
                labels=formatted_labels,
            )
            truncated_body = self._message_limiter.truncate(
                context=context,
                body=formatted_body,
                limit=self._tg_message_limit,
            )
            message = self._create_pr_message(
                pull_request, truncated_body, formatted_labels
            )
            render_result = sulguk.transform_html(
                message, base_url="https://github.com"
            )

        send_webhook(
            payload=self._create_payload(render_result),
            url=f"https://api.telegram.org/bot{self._bot_token}/sendMessage",
            attempts=self._attempt_count,
        )

    def _create_payload(self, render_result: sulguk.RenderResult) -> dict:
        for e in render_result.entities:
            e.pop("language", None)

        payload = {
            "text": render_result.text,
            "entities": render_result.entities,
            "disable_web_page_preview": True,
        }
        payload["chat_id"] = self._chat_id

        if self._message_thread_id is not None:
            payload["message_thread_id"] = self._message_thread_id

        return payload

    def _create_issue_message(self, issue: Issue, body: str, labels: str) -> str:
        template = self._custom_template or ISSUE_TEMPLATE
        return template.format(
            id=issue.id,
            user=issue.user,
            title=issue.title,
            labels=labels,
            url=issue.url,
            body=body,
            repository=issue.repository,
            promo="<a href='/reagento/relator'>sent via relator</a>",
        )

    def _create_pr_message(self, pr: PullRequest, body: str, labels: str) -> str:
        """Create HTML message for pull request"""
        template = self._custom_template or PR_TEMPLATE
        return template.format(
            id=pr.id,
            user=pr.user,
            title=pr.title,
            labels=labels,
            url=pr.url,
            body=body,
            repository=pr.repository,
            additions=pr.additions,
            deletions=pr.deletions,
            head_ref=pr.head_ref,
            base_ref=pr.base_ref,
            promo="<a href='/reagento/relator'>sent via relator</a>",
        )


