"""Text metrics estimation for Excalidraw elements.

Estimates character advances and bounding boxes for Excalidraw's Virgil (hand-drawn)
and Cascadia fonts without requiring a headless browser during compilation.

Constants:
    CHAR_W_RATIO: Average width of a character relative to font size (width / font_size).
                  Initial default is 0.58, calibrated against Excalidraw font metrics.
    LINE_HEIGHT_RATIO: Line height relative to font size. Default is 1.25.
"""

from __future__ import annotations

CHAR_W_RATIO: float = 0.58
LINE_HEIGHT_RATIO: float = 1.25


def measure(text: str, font_size: float) -> tuple[float, float]:
    """Estimate (width, height) of text rendered at font_size.

    Accounts for multiline text separated by newlines.
    """
    if not text:
        return 0.0, 0.0

    lines = text.split("\n")
    char_w = CHAR_W_RATIO * font_size
    line_h = LINE_HEIGHT_RATIO * font_size

    max_line_len = max(len(line) for line in lines)
    width = max_line_len * char_w
    height = len(lines) * line_h
    return width, height


def wrap(text: str, font_size: float, max_width: float) -> list[str]:
    """Greedy word wrap that preserves explicit newlines and hard-breaks oversized words.

    Returns a list of wrapped line strings.
    """
    if not text:
        return []

    char_w = CHAR_W_RATIO * font_size
    max_chars = max(1, int(max_width / char_w))

    wrapped_lines: list[str] = []

    for paragraph in text.split("\n"):
        if not paragraph.strip():
            wrapped_lines.append("")
            continue

        raw_words = paragraph.split(" ")
        # Handle oversized words by breaking them into chunks
        words: list[str] = []
        for word in raw_words:
            if len(word) > max_chars:
                for i in range(0, len(word), max_chars):
                    words.append(word[i : i + max_chars])
            else:
                words.append(word)

        current_line: list[str] = []
        current_len = 0

        for word in words:
            word_len = len(word)
            # Check length if appended (including space if current_line has words)
            needed = word_len if not current_line else current_len + 1 + word_len
            if needed <= max_chars:
                current_line.append(word)
                current_len = needed
            else:
                if current_line:
                    wrapped_lines.append(" ".join(current_line))
                current_line = [word]
                current_len = word_len

        if current_line:
            wrapped_lines.append(" ".join(current_line))

    return wrapped_lines
