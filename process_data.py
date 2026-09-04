#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.14"
# dependencies = [
#   "datasets",
#   "pandas[excel]",
# ]
# ///

import re
from pathlib import Path
from typing import NamedTuple

import pandas as pd

from datasets import ClassLabel, Dataset, Features, Sequence, Value

DATASETS_DIR = Path(__file__).parent / "datasets"
HUB_REPO_ID = "isa-ras/frustration_dataset_test"
LABELS = {"E'", "M'", "I'", "E", "M", "I", "e", "m", "i", "p", "f"}
BLACKLIST = {
    "Анализ - КузнецоваЮ.М..xlsx",
}

class FileAndLabelPattern(NamedTuple):
    file: Path
    num_labelers: int


if __name__ == "__main__":
    dataset2file_and_label_pattern: dict[str, FileAndLabelPattern] = {}
    label_pattern = re.compile(
        "|".join(re.escape(label) for label in sorted(LABELS, key=len, reverse=True))
    )

    for file in list(DATASETS_DIR.glob("*.xlsx")):
        if file.name in BLACKLIST:
            continue
        dataset_name = file.stem.split(" - ", maxsplit=1)[0]
        labeler_count = len(pd.read_excel(file, nrows=0, engine="openpyxl").columns) - 1
        if (
            dataset_name not in dataset2file_and_label_pattern
            or labeler_count
            > dataset2file_and_label_pattern[dataset_name].num_labelers
        ):
            dataset2file_and_label_pattern[dataset_name] = FileAndLabelPattern(
                file, labeler_count
            )

    for dataset_name, (file, _) in dataset2file_and_label_pattern.items():
        data = pd.read_excel(file, engine="openpyxl")
        label_columns = data.columns.drop("текст")
        if "источник" in label_columns:
            label_columns = label_columns.drop("источник")
        data[label_columns] = data[label_columns].apply(
            lambda column: column.fillna("").str.findall(label_pattern)
        )

        used_labels = data[label_columns].stack().explode().dropna().unique().tolist()
        class_label = ClassLabel(num_classes=len(used_labels), names=used_labels)
        single_label_data = data[
            data[label_columns].map(len).eq(1).all(axis="columns")
        ].copy()
        single_label_data[label_columns] = single_label_data[label_columns].map(
            lambda labels: labels[0]
        ).map(class_label.str2int)

        for revision, revision_data, label_feature in [
            ("single-label", single_label_data, class_label),
            ("multi-label", data, Sequence(class_label)),
        ]:
            features = Features(
                {"текст": Value("string")}
                | {
                    label_column: label_feature for label_column in label_columns
                } | ({"источник": Value("string")} if "источник" in data.columns else {})
            )
            Dataset.from_pandas(
                revision_data, features=features, preserve_index=False
            ).push_to_hub(
                HUB_REPO_ID, config_name=dataset_name, revision=revision
            )
