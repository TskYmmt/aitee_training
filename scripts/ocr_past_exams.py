"""
過去問PDFをNDLOCR-Liteでテキスト化するパイプライン
PDF -> 画像(pdftoppm) -> OCR(NDLOCR-Lite) -> txt/json

まず午前問題(am_qs)を処理し、その後に午後問題・解答等を処理する
"""

import os
import sys
import glob
import json
import shutil
import subprocess
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_DIR = os.path.join(BASE_DIR, "ref", "past_exams")
OUTPUT_DIR = os.path.join(BASE_DIR, "ref", "past_exams_ocr")
TMP_DIR = "/tmp/ocr_pipeline"
NDLOCR_DIR = os.path.join(BASE_DIR, "tools", "ndlocr-lite")
NDLOCR_VENV_PYTHON = os.path.join(NDLOCR_DIR, ".venv", "bin", "python3")
NDLOCR_SCRIPT = os.path.join(NDLOCR_DIR, "src", "ocr.py")


def pdf_to_images(pdf_path, img_dir, dpi=300):
    """PDFを画像に変換 (pdftoppm)"""
    os.makedirs(img_dir, exist_ok=True)
    cmd = [
        "pdftoppm", "-png", "-r", str(dpi),
        pdf_path, os.path.join(img_dir, "page")
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    images = sorted(glob.glob(os.path.join(img_dir, "page-*.png")))
    return images


def run_ocr(img_dir, out_dir):
    """NDLOCR-Liteでディレクトリ内の画像をOCR処理"""
    os.makedirs(out_dir, exist_ok=True)
    cmd = [
        NDLOCR_VENV_PYTHON, NDLOCR_SCRIPT,
        "--sourcedir", img_dir,
        "--output", out_dir
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.join(NDLOCR_DIR, "src"))
    if result.returncode != 0:
        print(f"    [OCR ERROR] {result.stderr[:200]}")
        return False
    return True


def merge_txt_files(out_dir, merged_path):
    """ページごとのtxtファイルを1つに結合"""
    txt_files = sorted(glob.glob(os.path.join(out_dir, "*.txt")))
    with open(merged_path, "w", encoding="utf-8") as out:
        for tf in txt_files:
            page_name = os.path.basename(tf).replace(".txt", "")
            with open(tf, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                out.write(f"--- {page_name} ---\n")
                out.write(content + "\n\n")
    return len(txt_files)


def merge_json_files(out_dir, merged_path):
    """ページごとのjsonファイルを1つに結合"""
    json_files = sorted(glob.glob(os.path.join(out_dir, "*.json")))
    pages = []
    for jf in json_files:
        with open(jf, "r", encoding="utf-8") as f:
            data = json.load(f)
        pages.append({
            "page": os.path.basename(jf).replace(".json", ""),
            "data": data
        })
    with open(merged_path, "w", encoding="utf-8") as out:
        json.dump(pages, out, ensure_ascii=False, indent=2)
    return len(pages)


def process_pdf(pdf_path):
    """1つのPDFを処理"""
    basename = os.path.splitext(os.path.basename(pdf_path))[0]
    img_dir = os.path.join(TMP_DIR, "images", basename)
    ocr_out_dir = os.path.join(TMP_DIR, "ocr_out", basename)
    final_dir = os.path.join(OUTPUT_DIR)
    os.makedirs(final_dir, exist_ok=True)

    # 1. PDF -> 画像
    print(f"  [pdf2img] {basename}...")
    images = pdf_to_images(pdf_path, img_dir)
    print(f"    {len(images)} pages")

    # 2. OCR
    print(f"  [ocr] processing {len(images)} pages...")
    t0 = time.time()
    success = run_ocr(img_dir, ocr_out_dir)
    elapsed = time.time() - t0
    if not success:
        return False
    print(f"    done in {elapsed:.1f}s ({elapsed/max(len(images),1):.1f}s/page)")

    # 3. 結果を結合
    merged_txt = os.path.join(final_dir, f"{basename}.txt")
    merged_json = os.path.join(final_dir, f"{basename}.json")
    n_txt = merge_txt_files(ocr_out_dir, merged_txt)
    n_json = merge_json_files(ocr_out_dir, merged_json)
    print(f"  [merge] {n_txt} pages -> {merged_txt}")

    # 4. 一時ファイル削除
    shutil.rmtree(img_dir, ignore_errors=True)
    shutil.rmtree(ocr_out_dir, ignore_errors=True)

    return True


def main():
    # 処理対象のPDFパターン（優先順位順）
    patterns = [
        ("午前問題", "*_ap_am_qs.pdf"),
        ("午前解答", "*_ap_am_ans.pdf"),
        ("午後問題", "*_ap_pm_qs.pdf"),
        ("午後解答", "*_ap_pm_ans.pdf"),
        ("午後採点講評", "*_ap_pm_cmnt.pdf"),
    ]

    # コマンドライン引数で処理対象を絞れる (am_qs, all)
    target = sys.argv[1] if len(sys.argv) > 1 else "am_qs"

    if target == "am_qs":
        patterns = [patterns[0]]  # 午前問題のみ
    elif target == "am":
        patterns = patterns[:2]   # 午前問題＋解答
    # else: all

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TMP_DIR, exist_ok=True)

    print(f"=== 過去問PDF OCR パイプライン ===")
    print(f"  対象: {target}")
    print(f"  出力: {OUTPUT_DIR}\n")

    total = 0
    success = 0
    for label, pattern in patterns:
        pdfs = sorted(glob.glob(os.path.join(PDF_DIR, pattern)))
        print(f"\n[{label}] {len(pdfs)} files")
        print("=" * 50)

        for i, pdf in enumerate(pdfs):
            total += 1
            name = os.path.basename(pdf)

            # 既にOCR済みならスキップ
            expected_txt = os.path.join(OUTPUT_DIR, name.replace(".pdf", ".txt"))
            if os.path.exists(expected_txt):
                print(f"  ({i+1}/{len(pdfs)}) [skip] {name}")
                success += 1
                continue

            print(f"\n  ({i+1}/{len(pdfs)}) {name}")
            try:
                if process_pdf(pdf):
                    success += 1
            except Exception as e:
                print(f"  [FATAL] {e}")

    print(f"\n=== 完了: {success}/{total} files ===")


if __name__ == "__main__":
    main()
