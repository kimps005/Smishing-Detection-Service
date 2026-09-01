"""FP32와 INT8 동적 양자화 SMS 분류기를 같은 데이터로 비교한다.

원본 서비스와 같은 토크나이저, 전처리, 키워드 보정을 사용한다. 각 변형은
별도 프로세스에서 실행해야 RSS 메모리 측정값이 서로 섞이지 않는다.
"""

from __future__ import annotations

import argparse
import gc
import json
import os
import platform
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import psutil
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support

from server import predictor


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET = PROJECT_ROOT / "output" / "quantization_benchmark_2800" / "metadata.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "output" / "quantization_benchmark_2800" / "quantization_results"
DEFAULT_ARTIFACT_DIR = PROJECT_ROOT / "models"
LABELS = list(sorted(predictor.CATEGORIES))


def rss_mb(process: psutil.Process) -> float:
    return round(process.memory_info().rss / (1024 * 1024), 2)


def apply_keyword_boosts(logits: np.ndarray, raw_texts: list[str], cleaned_texts: list[str]) -> np.ndarray:
    """predictor.predict의 키워드 보정을 배치 추론에도 동일하게 적용한다."""
    adjusted = logits.copy()
    for row_idx, (raw_text, cleaned_text) in enumerate(zip(raw_texts, cleaned_texts)):
        for category_idx, boost_info in predictor.KEYWORD_BOOSTS.items():
            for keyword in boost_info.get("keywords", []):
                if keyword in raw_text or keyword in cleaned_text:
                    adjusted[row_idx, category_idx] += boost_info["weight"]
                    break
            for condition in boost_info.get("keyword_groups", []):
                if all(
                    any(keyword in raw_text or keyword in cleaned_text for keyword in group)
                    for group in condition
                ):
                    adjusted[row_idx, category_idx] += boost_info["weight"]
    return adjusted


def softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    exp_logits = np.exp(shifted)
    return exp_logits / exp_logits.sum(axis=1, keepdims=True)


def expected_calibration_error(confidences: np.ndarray, correct: np.ndarray, bins: int = 10) -> float:
    boundaries = np.linspace(0.0, 1.0, bins + 1)
    ece = 0.0
    for index in range(bins):
        lower, upper = boundaries[index], boundaries[index + 1]
        if index == bins - 1:
            mask = (confidences >= lower) & (confidences <= upper)
        else:
            mask = (confidences >= lower) & (confidences < upper)
        if not np.any(mask):
            continue
        ece += abs(correct[mask].mean() - confidences[mask].mean()) * mask.mean()
    return float(ece)


def load_model(variant: str, process: psutil.Process) -> tuple[nn.Module, object, dict]:
    """서비스와 동일한 모델을 로드하고 필요 시 Linear 계층만 INT8로 변환한다."""
    predictor.prepare_models()
    before_load_rss = rss_mb(process)
    load_started = time.perf_counter()

    tokenizer = predictor._from_pretrained(predictor.AutoTokenizer, predictor.MODEL_NAME)
    model = predictor.SMSClassifier()
    state_dict = torch.load(predictor.resolve_source_model_path(), map_location="cpu", weights_only=True)
    model.load_state_dict(state_dict, strict=False)
    del state_dict
    model.eval()
    gc.collect()

    load_seconds = time.perf_counter() - load_started
    fp32_rss = rss_mb(process)
    quantize_seconds = 0.0
    quantized_linear_count = 0

    if variant == "int8_dynamic":
        if "x86" in torch.backends.quantized.supported_engines:
            torch.backends.quantized.engine = "x86"
        elif "fbgemm" in torch.backends.quantized.supported_engines:
            torch.backends.quantized.engine = "fbgemm"

        quantize_started = time.perf_counter()
        model = torch.ao.quantization.quantize_dynamic(
            model,
            {nn.Linear},
            dtype=torch.qint8,
            inplace=False,
        )
        model.eval()
        gc.collect()
        quantize_seconds = time.perf_counter() - quantize_started
        quantized_linear_count = sum(
            1
            for module in model.modules()
            if isinstance(module, torch.ao.nn.quantized.dynamic.Linear)
        )

    return model, tokenizer, {
        "rss_before_load_mb": before_load_rss,
        "rss_after_fp32_load_mb": fp32_rss,
        "rss_after_model_ready_mb": rss_mb(process),
        "load_seconds": round(load_seconds, 4),
        "quantize_seconds": round(quantize_seconds, 4),
        "quantized_linear_layers": quantized_linear_count,
        "quantized_engine": torch.backends.quantized.engine,
    }


@torch.inference_mode()
def predict_batch(model: nn.Module, tokenizer, texts: list[str]) -> tuple[np.ndarray, np.ndarray]:
    cleaned_texts = [predictor._clean(text) for text in texts]
    encoded = tokenizer(
        cleaned_texts,
        max_length=predictor.MAX_LENGTH,
        padding="max_length",
        truncation=True,
        return_tensors="pt",
    )
    logits = model(encoded["input_ids"], encoded["attention_mask"])
    logits_np = logits.cpu().float().numpy()
    probs = softmax(apply_keyword_boosts(logits_np, texts, cleaned_texts))
    return probs.argmax(axis=1).astype(int), probs


def evaluate_quality(model: nn.Module, tokenizer, frame: pd.DataFrame, batch_size: int) -> tuple[dict, pd.DataFrame]:
    all_predictions: list[int] = []
    all_probabilities: list[np.ndarray] = []
    texts = frame["text"].astype(str).tolist()

    started = time.perf_counter()
    for start in range(0, len(texts), batch_size):
        batch_texts = texts[start:start + batch_size]
        predictions, probabilities = predict_batch(model, tokenizer, batch_texts)
        all_predictions.extend(predictions.tolist())
        all_probabilities.extend(probabilities)
    elapsed = time.perf_counter() - started

    y_true = frame["label_idx"].astype(int).to_numpy()
    y_pred = np.asarray(all_predictions, dtype=int)
    probabilities = np.asarray(all_probabilities, dtype=float)
    confidences = probabilities.max(axis=1)
    correct = (y_true == y_pred).astype(float)

    precision, recall, f1, support = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=LABELS,
        zero_division=0,
    )
    per_class = {
        predictor.CATEGORIES[label]: {
            "precision": round(float(precision[index]), 6),
            "recall": round(float(recall[index]), 6),
            "f1": round(float(f1[index]), 6),
            "support": int(support[index]),
        }
        for index, label in enumerate(LABELS)
    }
    one_hot = np.eye(len(LABELS))[y_true]

    metrics = {
        "samples": int(len(frame)),
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 6),
        "macro_precision": round(float(np.mean(precision)), 6),
        "macro_recall": round(float(np.mean(recall)), 6),
        "macro_f1": round(float(np.mean(f1)), 6),
        "multiclass_brier": round(float(np.mean(np.sum((probabilities - one_hot) ** 2, axis=1))), 6),
        "ece_10_bins": round(expected_calibration_error(confidences, correct), 6),
        "mean_confidence": round(float(confidences.mean()), 6),
        "high_confidence_errors": int(((confidences >= 0.9) & (y_true != y_pred)).sum()),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=LABELS).tolist(),
        "per_class": per_class,
        "batched_evaluation_seconds": round(elapsed, 4),
        "batched_samples_per_second": round(float(len(frame) / elapsed), 4),
    }
    predictions_frame = frame[["file_name", "label_idx", "category", "sub_category", "text"]].copy()
    predictions_frame["predicted_label"] = y_pred
    predictions_frame["predicted_category"] = [predictor.CATEGORIES[label] for label in y_pred]
    predictions_frame["confidence"] = confidences
    predictions_frame["is_correct"] = y_true == y_pred
    return metrics, predictions_frame


def measure_latency(
    model: nn.Module,
    tokenizer,
    frame: pd.DataFrame,
    per_category: int,
) -> dict:
    selected = (
        frame.groupby("label_idx", group_keys=False, sort=True)
        .head(per_category)
        .sort_values(["label_idx", "file_name"])
    )
    texts = selected["text"].astype(str).tolist()
    warmup_texts = texts[: min(10, len(texts))]
    for text in warmup_texts:
        predict_batch(model, tokenizer, [text])

    latencies_ms: list[float] = []
    for text in texts:
        started = time.perf_counter()
        predict_batch(model, tokenizer, [text])
        latencies_ms.append((time.perf_counter() - started) * 1000)

    latencies = np.asarray(latencies_ms)
    return {
        "samples": int(len(latencies)),
        "p50_ms": round(float(np.percentile(latencies, 50)), 3),
        "p95_ms": round(float(np.percentile(latencies, 95)), 3),
        "p99_ms": round(float(np.percentile(latencies, 99)), 3),
        "mean_ms": round(float(latencies.mean()), 3),
        "min_ms": round(float(latencies.min()), 3),
        "max_ms": round(float(latencies.max()), 3),
    }


def save_quantized_state(model: nn.Module, output_dir: Path) -> tuple[Path, float]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "sms_category_model_int8_dynamic_state_dict.pt"
    torch.save(model.state_dict(), output_path)
    return output_path, round(output_path.stat().st_size / (1024 * 1024), 2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FP32/INT8 동적 양자화 SMS 분류기 벤치마크")
    parser.add_argument("--variant", choices=["fp32", "int8_dynamic"], required=True)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR,
                        help="양자화 모델을 저장할 배포 디렉터리")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--latency-per-category", type=int, default=20)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--limit", type=int, default=None, help="빠른 점검용 전체 샘플 제한")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.threads <= 0 or args.batch_size <= 0 or args.latency_per_category <= 0:
        raise ValueError("threads, batch-size, latency-per-category는 1 이상이어야 합니다.")
    if not args.dataset.exists():
        raise FileNotFoundError(f"평가 데이터가 없습니다: {args.dataset}")

    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    frame = pd.read_csv(args.dataset)
    if args.limit is not None:
        frame = frame.groupby("label_idx", group_keys=False, sort=True).head(max(1, args.limit // len(LABELS)))
    frame = frame.reset_index(drop=True)
    if frame.empty:
        raise ValueError("평가할 데이터가 없습니다.")

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    process = psutil.Process(os.getpid())
    print(f"variant={args.variant}; samples={len(frame)}; threads={args.threads}", flush=True)

    model, tokenizer, load_metrics = load_model(args.variant, process)
    quality_metrics, predictions = evaluate_quality(model, tokenizer, frame, args.batch_size)
    latency_metrics = measure_latency(model, tokenizer, frame, args.latency_per_category)

    source_size_mb = round(predictor.resolve_source_model_path().stat().st_size / (1024 * 1024), 2)
    artifact = {"source_checkpoint_mb": source_size_mb}
    if args.variant == "int8_dynamic":
        quantized_path, quantized_size_mb = save_quantized_state(model, args.artifact_dir)
        artifact.update({
            "quantized_state_dict_path": str(quantized_path),
            "quantized_state_dict_mb": quantized_size_mb,
            "size_reduction_percent": round((1 - quantized_size_mb / source_size_mb) * 100, 2),
        })

    result = {
        "variant": args.variant,
        "dataset": {
            "path": str(args.dataset),
            "samples": int(len(frame)),
            "category_counts": {str(key): int(value) for key, value in frame["category"].value_counts().sort_index().items()},
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "torch": torch.__version__,
            "quantized_engine": torch.backends.quantized.engine,
            "threads": args.threads,
        },
        "load_and_memory": load_metrics,
        "model_artifact": artifact,
        "quality": quality_metrics,
        "single_request_latency": latency_metrics,
    }
    metrics_path = output_dir / f"{args.variant}_metrics.json"
    predictions_path = output_dir / f"{args.variant}_predictions.csv"
    metrics_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    predictions.to_csv(predictions_path, index=False, encoding="utf-8-sig")
    print(f"metrics={metrics_path}", flush=True)
    print(f"predictions={predictions_path}", flush=True)
    print(
        "summary="
        f"accuracy:{quality_metrics['accuracy']}; "
        f"macro_f1:{quality_metrics['macro_f1']}; "
        f"p95_ms:{latency_metrics['p95_ms']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
