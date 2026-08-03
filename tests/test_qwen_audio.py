from __future__ import annotations

import unittest
from unittest import mock

from generate_subtitle_qwen_api import (
    QWEN_AUDIO_FILETRANS_MODEL,
    build_qwen_audio_context,
    is_qwen_audio_model,
    parse_funasr_transcription_result,
    poll_task,
    submit_filetrans,
    supports_speaker_diarization,
)


class QwenAudioAdapterTests(unittest.TestCase):
    def test_model_detection_and_speaker_support(self) -> None:
        self.assertTrue(is_qwen_audio_model(QWEN_AUDIO_FILETRANS_MODEL))
        self.assertTrue(supports_speaker_diarization(QWEN_AUDIO_FILETRANS_MODEL))
        self.assertFalse(is_qwen_audio_model("qwen3-asr-flash-filetrans"))

    def test_context_uses_rest_messages_shape_and_400_character_limit(self) -> None:
        context = build_qwen_audio_context("词表" + ("x" * 500))

        self.assertEqual(context[0]["role"], "user")
        content = context[0]["content"][0]
        self.assertEqual(content["type"], "input_text")
        self.assertEqual(len(content["text"]), 400)

    @mock.patch("generate_subtitle_qwen_api.requests.post")
    def test_submit_sends_qwen_audio_file_urls_vocabulary_and_context(
        self,
        post: mock.Mock,
    ) -> None:
        response = mock.Mock()
        response.json.return_value = {
            "output": {"task_id": "task-qwen-audio", "task_status": "PENDING"}
        }
        post.return_value = response

        task_id = submit_filetrans(
            "https://dashscope.aliyuncs.com",
            "secret",
            "oss://temporary/audio.wav",
            language="zh",
            enable_words=True,
            enable_itn=False,
            model=QWEN_AUDIO_FILETRANS_MODEL,
            enable_speaker=True,
            vocabulary_id="vocab-qwen-audio",
            hotwords=["张三", "李四"],
            hotword_weight=5,
            context=build_qwen_audio_context("领域词表"),
        )

        self.assertEqual(task_id, "task-qwen-audio")
        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["model"], QWEN_AUDIO_FILETRANS_MODEL)
        self.assertEqual(payload["input"]["file_urls"], ["oss://temporary/audio.wav"])
        self.assertEqual(payload["input"]["context"][0]["role"], "user")
        self.assertEqual(payload["parameters"]["language_hints"], ["zh"])
        self.assertTrue(payload["parameters"]["diarization_enabled"])
        self.assertEqual(payload["parameters"]["vocabulary_id"], "vocab-qwen-audio")
        self.assertEqual(payload["parameters"]["vocabulary"], {"张三": 5, "李四": 5})
        self.assertNotIn("enable_words", payload["parameters"])
        self.assertNotIn("enable_itn", payload["parameters"])
        response.raise_for_status.assert_called_once_with()

    @mock.patch("generate_subtitle_qwen_api.requests.get")
    def test_poll_reads_qwen_audio_subtask_result(self, get: mock.Mock) -> None:
        response = mock.Mock()
        response.json.return_value = {
            "output": {
                "task_status": "SUCCEEDED",
                "results": [
                    {
                        "subtask_status": "SUCCEEDED",
                        "transcription_url": "https://result.example/qwen-audio.json",
                    }
                ],
            },
            "usage": {"duration": 12},
        }
        get.return_value = response

        result_url, usage = poll_task(
            "https://dashscope.aliyuncs.com",
            "secret",
            "task-qwen-audio",
            interval=0,
            timeout=1,
            model=QWEN_AUDIO_FILETRANS_MODEL,
        )

        self.assertEqual(result_url, "https://result.example/qwen-audio.json")
        self.assertEqual(usage, {"duration": 12})

    def test_parse_maps_qwen_audio_sentence_speaker_to_items(self) -> None:
        result = parse_funasr_transcription_result(
            {
                "transcripts": [
                    {
                        "text": "你好。",
                        "sentences": [
                            {
                                "language": "zh",
                                "speaker_id": 2,
                                "words": [
                                    {
                                        "begin_time": 100,
                                        "end_time": 300,
                                        "text": "你好",
                                        "punctuation": "。",
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        )

        self.assertEqual(result["language"], "zh")
        self.assertEqual(result["items"], [{
            "text": "你好。",
            "start": 100,
            "end": 300,
            "speaker": "2",
        }])


if __name__ == "__main__":
    _ = unittest.main()
