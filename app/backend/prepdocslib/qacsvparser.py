import csv
from collections.abc import AsyncGenerator
from typing import IO, Optional

from .page import Page
from .parser import Parser


class QACsvParser(Parser):
    """
    Concrete parser that can parse Q&A CSV files into Page objects.
    Expected format: CSV with at least two columns - Question and Answer.
    Each row becomes a Page object with the question and answer combined.
    """

    async def parse(self, content: IO) -> AsyncGenerator[Page, None]:
        # Check if content is in bytes (binary file) and decode to string
        content_str: str
        if isinstance(content, (bytes, bytearray)):
            content_str = content.decode("utf-8")
        elif hasattr(content, "read"):  # Handle BufferedReader
            content_str = content.read().decode("utf-8")

        # Create a CSV reader from the text content
        reader = csv.reader(content_str.splitlines())
        offset = 0

        # Get the header row to identify question and answer columns
        headers = next(reader, None)
        if not headers:
            return
            
        # Try to find question and answer columns
        question_idx = -1
        answer_idx = -1
        
        for i, header in enumerate(headers):
            header_lower = header.lower()
            if "question" in header_lower or "q" == header_lower:
                question_idx = i
            elif "answer" in header_lower or "a" == header_lower:
                answer_idx = i
        
        # If we couldn't find the columns, assume first two columns
        if question_idx == -1 or answer_idx == -1:
            question_idx = 0
            answer_idx = 1
            
        for i, row in enumerate(reader):
            if len(row) > max(question_idx, answer_idx):
                question = row[question_idx]
                answer = row[answer_idx]
                # Format as Q&A pair
                page_text = f"Question: {question}\nAnswer: {answer}"
                yield Page(i, offset, page_text)
                offset += len(page_text) + 1  # Account for newline character