from dataclasses import field, dataclass

from bs4 import BeautifulSoup, NavigableString, Tag


@dataclass
class TruncateHtmlState:
    count: int = field(default=0)
    done: bool = field(default=False)


class TruncateHTML:
    def __init__(self):
        self._ellipsis = "..."

    def _walk(
            self,
            node: Tag | NavigableString,
            state: TruncateHtmlState,
            max_length: int
    ) -> bool:
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
