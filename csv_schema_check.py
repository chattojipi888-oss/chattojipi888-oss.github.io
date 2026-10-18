"""CSV設備ログの列数・ヘッダー検証例（標準ライブラリのみ）。

CSVの構造だけを検査する。時刻順序や状態値の意味は別途検証が必要。
"""
import csv
from pathlib import Path


def validate_csv(path, expected=("timestamp", "status"), *,
                 max_bytes=1_048_576, max_rows=1000):
    """検証済みの辞書行を返す。不正入力は ValueError にする。"""
    path = Path(path)
    if path.stat().st_size > max_bytes:
        raise ValueError("CSVがサイズ上限を超えています")
    if not expected or len(set(expected)) != len(expected):
        raise ValueError("期待するヘッダーの指定が不正です")
    records = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f, strict=True)
            header = next(reader, None)
            if not header:
                raise ValueError("ヘッダーがありません")
            if len(header) != len(set(header)):
                raise ValueError("ヘッダー名が重複しています")
            if header != list(expected):
                raise ValueError(f"列名または順序が違います: {header!r}")
            for row in reader:
                if len(row) != len(header):
                    raise ValueError(
                        f"CSV列数不一致（物理行 {reader.line_num}）:"
                        f" 期待{len(header)}列、実際{len(row)}列"
                    )
                if any(not cell.strip() for cell in row):
                    raise ValueError(f"空欄があります（物理行 {reader.line_num}）")
                if len(records) >= max_rows:
                    raise ValueError("CSVが行数上限を超えています")
                records.append(dict(zip(header, row)))
    except (csv.Error, UnicodeError) as exc:
        raise ValueError(f"CSVを解析できません: {exc}") from exc
    if not records:
        raise ValueError("データ行がありません")
    return records


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        raise SystemExit("使い方: python3 csv_schema_check.py 設備ログ.csv")
    rows = validate_csv(sys.argv[1])
    print(f"構造チェック成功: {len(rows)}レコード")
