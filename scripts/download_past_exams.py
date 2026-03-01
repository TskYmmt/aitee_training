"""
IPA公式サイトから応用情報技術者試験(AP)の過去問PDFを一括ダウンロードするスクリプト

出典: IPA 独立行政法人 情報処理推進機構
https://www.ipa.go.jp/shiken/mondai-kaiotu/index.html
"""

import os
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

INDEX_URL = "https://www.ipa.go.jp/shiken/mondai-kaiotu/index.html"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "ref", "past_exams")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}
DELAY = 2  # サーバ負荷軽減のため2秒間隔


def get_year_pages():
    """過去問インデックスページから各年度ページのURLを取得"""
    resp = requests.get(INDEX_URL, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    year_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if re.search(r"/shiken/mondai-kaiotu/\d{4}", href):
            url = urljoin(INDEX_URL, href)
            if url not in year_links:
                year_links.append(url)

    return sorted(year_links)


def get_ap_pdfs(year_url):
    """各年度ページからファイル名に _ap_ を含むPDFリンクを抽出"""
    resp = requests.get(year_url, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    pdfs = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.endswith(".pdf") and "_ap_" in href:
            pdf_url = urljoin(year_url, href)
            if pdf_url not in pdfs:
                pdfs.append(pdf_url)

    return pdfs


def download_pdf(url, output_dir):
    """PDFをダウンロードして保存"""
    filename = os.path.basename(url)
    save_path = os.path.join(output_dir, filename)

    if os.path.exists(save_path):
        print(f"  [skip] {filename} (already exists)")
        return

    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()

    with open(save_path, "wb") as f:
        f.write(resp.content)

    size_kb = len(resp.content) / 1024
    print(f"  [done] {filename} ({size_kb:.0f} KB)")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=== IPA 応用情報技術者試験 過去問PDF 一括ダウンロード ===\n")

    print("[1/3] 年度ページ一覧を取得中...")
    year_pages = get_year_pages()
    print(f"  {len(year_pages)} 年度分を検出\n")

    all_pdfs = []
    print("[2/3] 各年度からAP PDFリンクを抽出中...")
    for yp in year_pages:
        label = re.search(r"/(\d{4}[a-z]\d{2})\.html", yp)
        label = label.group(1) if label else yp
        pdfs = get_ap_pdfs(yp)
        print(f"  {label}: {len(pdfs)} files")
        all_pdfs.extend(pdfs)
        time.sleep(DELAY)

    print(f"\n  合計 {len(all_pdfs)} PDFファイル\n")

    print("[3/3] PDFをダウンロード中...")
    for i, pdf_url in enumerate(all_pdfs):
        filename = os.path.basename(pdf_url)
        print(f"  ({i+1}/{len(all_pdfs)}) {filename}")
        try:
            download_pdf(pdf_url, OUTPUT_DIR)
        except Exception as e:
            print(f"  [error] {e}")
        time.sleep(DELAY)

    print(f"\n=== 完了: {len(all_pdfs)} files -> {OUTPUT_DIR} ===")


if __name__ == "__main__":
    main()
