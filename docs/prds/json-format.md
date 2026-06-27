# JSON Format PRD - LLM Benchmark Studio

## 1. 目标

本文定义 LLM Benchmark Studio 最终 JSON 格式，包括 normalized dataset JSON、API result JSON、ZIP 导出 JSON。所有 JSON 使用 UTF-8，不包含 provider API key，不保存模型 think 内容。

## 2. Normalized Dataset JSON

文件位置：

```text
data/benchmark_datasets/{dataset_name}.json
```

格式：

```json
{
  "source": {
    "dataset_name": "mmlu",
    "display_name": "MMLU",
    "subset": "all",
    "source_language": "en",
    "activate": true,
    "task_type": "multiple_choice",
    "answer_format": {
      "type": "single_option_letter",
      "valid_values": ["A", "B", "C", "D"]
    },
    "raw_source": {
      "type": "huggingface",
      "hf_path": "cais/mmlu",
      "hf_config": "all",
      "split": "test",
      "raw_path": "benchmark_datasets/raw/mmlu/test.jsonl"
    },
    "field_mapping": {
      "question": "question",
      "choices": "choices[] mapped to A/B/C/D",
      "answer": "answer integer index mapped to A/B/C/D"
    },
    "metadata_keep_fields": ["subject"],
    "ignored_fields": ["dev examples", "auxiliary split bookkeeping"],
    "benchmark_prompt": "You are answering a benchmark multiple-choice question. Return only A, B, C, or D.",
    "judge_prompt": "You are judging whether a model answer matches the gold answer. Return strict JSON only.",
    "regex_judge_rule": {
      "purpose": "Run regex judge for an existing llm_response without overwriting llm_judge.",
      "write_target": "regex_judge[]",
      "must_not_modify": ["question", "llm_response", "llm_judge"]
    }
  },
  "questions": [
    {
      "sample_id": "mmlu-00000001",
      "language": "en",
      "activate": true,
      "question": {
        "question_stem": "What is ...?",
        "options": {
          "A": "Option A",
          "B": "Option B",
          "C": "Option C",
          "D": "Option D"
        },
        "answer": "A"
      },
      "llm_response": {},
      "llm_judge": {},
      "regex_judge": [],
      "metadata": {
        "task_type": "multiple_choice",
        "subject": "abstract_algebra"
      }
    }
  ]
}
```

## 3. Benchmark Result JSON

Django 从 PostgreSQL 组合后返回，不要求直接回写 dataset JSON。

```json
{
  "result_id": "uuid",
  "dataset": {
    "id": "uuid",
    "name": "mmlu",
    "subset": "all",
    "source_language": "en"
  },
  "sample": {
    "id": "uuid",
    "sample_id": "mmlu-00000001",
    "question": "What is ...?",
    "choices": {
      "A": "Option A",
      "B": "Option B",
      "C": "Option C",
      "D": "Option D"
    },
    "gold_answer": "A",
    "language": "en",
    "metadata": {}
  },
  "llm_response": {
    "provider": "ollama",
    "model": "gpt-oss:20b",
    "supports_think": true,
    "context_length": 65536,
    "prompt": "You are answering a benchmark multiple-choice question...",
    "raw_response": "A",
    "final_answer": "A",
    "normalized_answer": "A",
    "usage": {
      "prompt_tokens": null,
      "completion_tokens": null,
      "total_tokens": null
    },
    "latency_ms": 1234,
    "status": "succeeded",
    "error_message": null,
    "created_at": "2026-06-27T15:30:00Z"
  },
  "llm_judge": {
    "judge_provider": "ollama",
    "judge_model": "gpt-oss:20b",
    "judge_prompt": "Compare the model answer with the gold answer...",
    "judge_raw_response": "{\"match\": true}",
    "match": true,
    "normalized_gold_answer": "A",
    "normalized_model_answer": "A",
    "score": 1.0,
    "reason": "The model answer matches the gold answer.",
    "created_at": "2026-06-27T15:31:00Z"
  },
  "regex_judge": [
    {
      "judge_provider": "ollama",
      "judge_model": "qwen3:32b",
      "judge_prompt": "Compare the model answer with the gold answer...",
      "judge_raw_response": "{\"match\": true}",
      "match": true,
      "normalized_gold_answer": "A",
      "normalized_model_answer": "A",
      "score": 1.0,
      "reason": "The answer is still correct.",
      "created_at": "2026-06-27T15:45:00Z"
    }
  ],
  "task": {
    "task_id": "uuid",
    "task_type": "benchmark",
    "status": "succeeded",
    "created_at": "2026-06-27T15:29:00Z",
    "finished_at": "2026-06-27T15:30:05Z"
  }
}
```

## 4. Translation JSON

```json
{
  "translation_id": "uuid",
  "source_sample_id": "uuid",
  "source_language": "en",
  "target_language": "fr",
  "translator_provider": "ollama",
  "translator_model": "gpt-oss:20b",
  "translated_question": "Question translated to French...",
  "translated_choices": {
    "A": "Option A translated",
    "B": "Option B translated",
    "C": "Option C translated",
    "D": "Option D translated"
  },
  "translated_gold_answer": "A",
  "status": "succeeded",
  "error_message": null,
  "created_at": "2026-06-27T15:35:00Z"
}
```

## 5. ZIP Export Format

导出 API：

```text
GET /api/results/export
```

ZIP 文件名：

```text
llm-benchmark-results-YYYYMMDD-HHMMSS.zip
```

ZIP 内容：

```text
manifest.json
results/
  benchmark_results.json
  translations.json
  tasks.json
```

`manifest.json`：

```json
{
  "exported_at": "2026-06-27T15:50:00Z",
  "app": "LLM Benchmark Studio",
  "format_version": "1.0",
  "filters": {
    "dataset_id": null,
    "model_id": null,
    "language": null,
    "status": null
  },
  "counts": {
    "benchmark_results": 120,
    "translations": 20,
    "tasks": 140
  }
}
```

`results/benchmark_results.json`：

```json
[
  {
    "result_id": "uuid",
    "dataset": {},
    "sample": {},
    "llm_response": {},
    "llm_judge": {},
    "regex_judge": [],
    "task": {}
  }
]
```

## 6. 约束

- `activate` 必须存在于 dataset、sample、model、language 配置。
- `source.activate` 和每个 question 的 `activate` 必须存在。
- `language` 必须存在于 question 和 result。
- normalized dataset JSON 顶层必须包含 `source` 和 `questions`。
- 每个 question 必须包含 `question.question_stem`、`question.options`、`question.answer`。
- parser 后的 `llm_response` 和 `llm_judge` 是空对象，`regex_judge` 是空数组。
- `llm_response` 支持多个模型结果，数据库层通过 run 表表达，导出时每个 run 是一个 result item。
- `llm_judge` 是首次 judge。
- `regex_judge` 是数组，允许多次正则判断。
- 不保存 think。
- 不导出 API key。
