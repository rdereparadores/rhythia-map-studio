"""Structured messages cross service/worker boundaries without depending on Qt.

Message remains a string for logs and existing progress consumers. Translation
uses its source and parameters directly, never parses the formatted text.
"""


class Message(str):
    def __new__(cls, template: str, **values):
        instance = super().__new__(cls, template.format(**values))
        instance.source = template
        instance.values = values
        return instance


class MessageError(ValueError):
    def __init__(self, template: str, **values):
        self.message = Message(template, **values)
        super().__init__(self.message)
