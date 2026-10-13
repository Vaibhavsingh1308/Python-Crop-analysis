"""
Crop Production Analysis (KDD approach)
Data source: data.gov.in -> "District-wise, Season-wise Crop Production Statistics"
             (Ministry of Agriculture & Farmers Welfare)

Usage:
    python crop_analysis.py --csv crop_production.csv
    python crop_analysis.py --csv crop_production.csv --top 10 --out top10_crops.png

KDD stages used:
    1. Selection        - load the dataset, keep the needed columns
    2. Preprocessing    - clean text, handle missing values, remove duplicates
    3. Transformation   - convert types, aggregate by crop
    4. Data mining      - group / compare crops by production
    5. Visualization    - bar chart of top N crops
    6. Interpretation   - print patterns found (conclusion)
"""

import argparse
import sys

import pandas as pd
import matplotlib

matplotlib.use("Agg")  # works on servers without a display
import matplotlib.pyplot as plt


# --------------------------------------------------------------------------
# 1. SELECTION
# --------------------------------------------------------------------------
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Normalise column names: "State_Name" / "state name" -> "state_name"
    df.columns = (
        df.columns.str.strip().str.lower().str.replace(r"[\s\-]+", "_", regex=True)
    )
    required = {"crop", "production"}
    missing = required - set(df.columns)
    if missing:
        sys.exit(f"CSV is missing required column(s): {missing}. Found: {list(df.columns)}")
    print(f"[Selection] Loaded {len(df):,} rows, {df.shape[1]} columns")
    return df


# --------------------------------------------------------------------------
# 2. PREPROCESSING  (handle missing values)
# --------------------------------------------------------------------------
def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    print("\n[Preprocessing] Missing values BEFORE cleaning:")
    print(df.isnull().sum().to_string())

    # Clean text columns
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].astype(str).str.strip().replace({"nan": pd.NA, "": pd.NA})

    # Production must be numeric; bad values (e.g. "NA", "-") become NaN
    df["production"] = pd.to_numeric(df["production"], errors="coerce")
    if "area" in df.columns:
        df["area"] = pd.to_numeric(df["area"], errors="coerce")

    # Rows with no crop name are useless
    df = df.dropna(subset=["crop"])

    # Missing production: fill with the median production of the same crop,
    # then drop anything still missing (crop with no valid values at all)
    df["production"] = df.groupby("crop")["production"].transform(
        lambda s: s.fillna(s.median())
    )
    df = df.dropna(subset=["production"])

    # Negative production is not valid
    df = df[df["production"] >= 0]

    before = len(df)
    df = df.drop_duplicates()
    print(f"\n[Preprocessing] Removed {before - len(df)} duplicate rows")
    print(f"[Preprocessing] Clean dataset: {len(df):,} rows")
    return df


# --------------------------------------------------------------------------
# 3 + 4. TRANSFORMATION & DATA MINING (group and compare crops)
# --------------------------------------------------------------------------
def mine(df: pd.DataFrame, top_n: int) -> pd.DataFrame:
    agg = {"production": ["sum", "mean", "count"]}
    summary = df.groupby("crop").agg(agg)
    summary.columns = ["total_production", "avg_production", "records"]
    summary = summary.sort_values("total_production", ascending=False)
    summary["share_pct"] = (
        summary["total_production"] / summary["total_production"].sum() * 100
    ).round(2)

    top = summary.head(top_n)
    print(f"\n[Data Mining] Top {top_n} crops by total production:")
    print(top.round(2).to_string())
    return summary


# --------------------------------------------------------------------------
# 5. VISUALIZATION
# --------------------------------------------------------------------------
def plot_top(summary: pd.DataFrame, top_n: int, out_file: str) -> None:
    top = summary.head(top_n).iloc[::-1]  # reverse so the biggest is on top
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(top.index, top["total_production"], color="#2e7d32")
    ax.set_title(f"Top {top_n} Crops by Total Production")
    ax.set_xlabel("Total production (as reported in dataset units)")
    ax.set_ylabel("Crop")
    ax.bar_label(bars, labels=[f"{v:,.0f}" for v in top["total_production"]], padding=3, fontsize=8)
    ax.margins(x=0.15)
    plt.tight_layout()
    fig.savefig(out_file, dpi=150)
    print(f"\n[Visualization] Chart saved to {out_file}")


# --------------------------------------------------------------------------
# 6. INTERPRETATION (conclusion)
# --------------------------------------------------------------------------
def conclude(df: pd.DataFrame, summary: pd.DataFrame, top_n: int) -> None:
    top = summary.head(top_n)
    print("\n[Conclusion] Patterns found:")
    print(f"  - Crops analysed: {len(summary)}")
    print(f"  - Highest producing crop: {top.index[0]} "
          f"({top['share_pct'].iloc[0]}% of total production)")
    print(f"  - Top {top_n} crops contribute {top['share_pct'].sum():.1f}% of all production")

    for col, label in [("state_name", "state"), ("season", "season"), ("crop_year", "year")]:
        if col in df.columns:
            best = df.groupby(col)["production"].sum().sort_values(ascending=False)
            print(f"  - Top {label} by production: {best.index[0]}")


def main() -> None:
    p = argparse.ArgumentParser(description="Crop production analysis")
    p.add_argument("--csv", required=True, help="Path to CSV downloaded from data.gov.in")
    p.add_argument("--top", type=int, default=10, help="How many top crops to show")
    p.add_argument("--out", default="top10_crops.png", help="Output chart file")
    a = p.parse_args()

    df = load_data(a.csv)
    df = preprocess(df)
    summary = mine(df, a.top)
    plot_top(summary, a.top, a.out)
    conclude(df, summary, a.top)


if __name__ == "__main__":
    main()
