from __future__ import annotations

import logging
import unittest

from app.core.llm_usage import log_chat_completion_usage


class LlmUsageLoggingTests(unittest.TestCase):
    def test_log_chat_completion_usage_emits_expected_extra_keys(self) -> None:
        logger = logging.getLogger("test_llm_usage")
        logger.setLevel(logging.INFO)
        records: list[logging.LogRecord] = []

        class ListHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                records.append(record)

        handler = ListHandler()
        logger.addHandler(handler)
        try:
            log_chat_completion_usage(
                logger,
                response_body={
                    "model": "gpt-test",
                    "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
                },
                session_id="sess-1",
                skill_id="session_grounded_qa",
                model_requested="fallback-model",
            )
        finally:
            logger.removeHandler(handler)

        self.assertEqual(len(records), 1)
        rec = records[0]
        self.assertEqual(rec.event, "llm.completion.usage")
        self.assertEqual(rec.session_id, "sess-1")
        self.assertEqual(rec.skill_id, "session_grounded_qa")
        self.assertEqual(rec.model, "gpt-test")
        self.assertEqual(rec.prompt_tokens, 10)
        self.assertEqual(rec.completion_tokens, 20)
        self.assertEqual(rec.total_tokens, 30)


if __name__ == "__main__":
    unittest.main()
