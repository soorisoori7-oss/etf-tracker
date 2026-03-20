"""
fetch_etf.py
-----------
yfinance를 사용해 ETHU / BITX / SOLT 의 최근 정규장 종가를 수집하고
data/etf-data.json 에 저장한다.

- 서버사이드 실행이므로 CORS / 프록시 불필요
- yfinance는 Yahoo Finance 데이터를 직접 파싱 → 403 우회
- 멱등성: 같은 날 재실행해도 같은 결과
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yfinance as yf

# ── 설정 ─────────────────────────────────────────
TICKERS = {
    "ETHU": "ethereum",
    "BITX": "bitcoin",
    "SOLT": "solana",
}

NY_TZ   = timezone(timedelta(hours=-5))   # EST (하계엔 -4이지만 종가 날짜 판단용으로 근사치 사용)
OUT_DIR = Path(__file__).parent.parent / "data"
OUT_FILE = OUT_DIR / "etf-data.json"

# ── 날짜 오버라이드 (workflow_dispatch input) ────
force_date = os.environ.get("FORCE_DATE", "").strip()


def fetch_latest_close(ticker: str) -> dict:
    """최근 5거래일 데이터에서 가장 마지막 유효 종가를 반환."""
    tk   = yf.Ticker(ticker)
    hist = tk.history(period="5d", interval="1d", auto_adjust=False)

    if hist.empty:
        raise ValueError(f"{ticker}: 데이터 없음")

    # 가장 마지막 유효 종가 행
    valid = hist["Close"].dropna()
    if valid.empty:
        raise ValueError(f"{ticker}: 유효 종가 없음")

    last_ts    = valid.index[-1]
    last_close = float(valid.iloc[-1])

    # 날짜를 뉴욕 시간대 기준으로 변환 (timestamp는 UTC)
    ny_date = last_ts.tz_convert("America/New_York").strftime("%Y-%m-%d")

    return {
        "close": round(last_close, 4),
        "date":  ny_date,
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    results  = {}
    errors   = []
    ref_date = None   # 3종목 공통 기준일

    for ticker, coin_id in TICKERS.items():
        try:
            data = fetch_latest_close(ticker)
            results[ticker] = data
            # 기준일: 첫 번째 성공 종목 날짜 사용
            if ref_date is None:
                ref_date = data["date"]
            print(f"  ✓ {ticker}: ${data['close']}  ({data['date']})")
        except Exception as e:
            errors.append(f"{ticker}: {e}")
            print(f"  ✗ {ticker}: {e}", file=sys.stderr)

    if not results:
        print("모든 종목 수집 실패 — JSON 미업데이트", file=sys.stderr)
        sys.exit(1)

    # ── 기존 JSON 로드 (fallback 병합용) ────────────
    existing = {}
    if OUT_FILE.exists():
        try:
            existing = json.loads(OUT_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    # ── 최종 JSON 조립 ──────────────────────────────
    # 실패 종목은 기존 값을 유지 (partial update)
    prices = existing.get("prices", {})
    for ticker, data in results.items():
        prices[ticker] = data

    output = {
        # 수집 메타
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ref_date":   ref_date or existing.get("ref_date"),
        "partial":    len(errors) > 0,
        "errors":     errors,

        # 종가 데이터 — 블로그에서 직접 읽는 부분
        # 구조: { "ETHU": { "close": 23.17, "date": "2026-03-20" }, ... }
        "prices": prices,
    }

    OUT_FILE.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"\n저장 완료: {OUT_FILE}")
    print(json.dumps(output, indent=2, ensure_ascii=False))

    # 부분 실패 시 경고 코드로 종료 (Actions에서 노란 경고로 표시)
    if errors:
        sys.exit(2)


if __name__ == "__main__":
    main()
