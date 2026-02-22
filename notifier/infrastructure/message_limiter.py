from dataclasses import dataclass, field

from bs4 import PageElement, NavigableString, Tag, BeautifulSoup

from notifier.application.interfaces import MessageLimiter, MessageContext


@dataclass
class TruncateHtmlState:
    count: int = field(default=0)
    done: bool = field(default=False)


class TruncateHTML:
    def __init__(self):
        self._ellipsis = "..."

    def _walk(
            self,
            node: PageElement,
            state: TruncateHtmlState,
            max_length: int
    ):
        if isinstance(node, NavigableString):
            text = node.text
            if state.count + len(text) <= max_length:
                state.count += len(text)
                return

            remaining = max_length - state.count
            if remaining <= 0:
                node.extract()
                state.done = True
                return

            cut_text = text[:remaining].rstrip() + self._ellipsis
            node.replace_with(cut_text)
            state.done = True
            return

        if isinstance(node, Tag):
            children = list(node.contents)
            for i, child in enumerate(children):
                self._walk(child, state, max_length)
                if state.done:
                    tags_deleted = children[i + 1:]
                    for tag_deleted in tags_deleted:
                        tag_deleted.extract()
                    break

    def render(
            self,
            raw_html: str,
            max_length: int
    ) -> str:

        soup = BeautifulSoup(raw_html, "html.parser")
        state = TruncateHtmlState(
            count=0
        )

        for node in soup.contents:
            self._walk(
                node=node,
                state=state,
                max_length=max_length
            )
            if state.done:
                break

        return str(soup)


class HtmlMessageLimiter(MessageLimiter):
    def __init__(self) -> None:
        self._truncator = TruncateHTML()

    def truncate(
            self,
            context: MessageContext,
            body: str,
            limit: int,
    ) -> str:
        base_message = context.build("<p></p>")
        available = limit - context.measure(base_message)

        if available <= 0 or not body:
            return "<p></p>"

        truncated = self._truncator.render(body, available)

        message = context.build(truncated)
        if context.measure(message) <= limit:
            return truncated

        overflow = context.measure(message) - limit
        reduced_available = max(0, available - overflow)
        if reduced_available <= 0:
            return "<p></p>"

        return self._truncator.render(body, reduced_available)
