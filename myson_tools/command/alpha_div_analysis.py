from skbio.diversity.alpha import shannon, simpson
from pathlib import Path
from math import log
import pandas as pd
import numpy as np
import argparse
import sys

class DiversityMetricsCalculator:
    def __init__(self, feature_table_path, metadata_path, output_path):
        self.feature_table_path = feature_table_path
        self.metadata_path = metadata_path
        self.output_path = output_path
        self.feature_table = None
        self.meta_seq = None
        self.merged = None
        self.final_df = None

    def load_feature_table(self):
        try:
            df = pd.read_csv(self.feature_table_path, sep="\t", skiprows=[0])
            df = df.set_index("#OTU ID").T
            df.index.name = "#Sample_ID"
            df["sample_code"] = df.index.map(self.extract_sample_code)
            self.feature_table = df
        except FileNotFoundError:
            raise FileNotFoundError(f"❌ Feature table file not found: {self.feature_table_path}")
        except pd.errors.ParserError as e:
            raise ValueError(f"❌ Failed to parse feature table file: {e}")
        except Exception as e:
            raise RuntimeError(f"❌ Unexpected error while loading feature table: {e}")

    def load_metadata(self):
        try:
            meta = pd.read_excel(self.metadata_path)
            meta["ID échantillon"] = meta["ID échantillon"].astype(str)\
                .str.replace("\u00A0", "", regex=False)\
                .str.replace(" ", "")\
                .str.strip()
            self.meta_seq = meta
        except FileNotFoundError:
            raise FileNotFoundError(f"❌ Metadata file not found: {self.metadata_path}")
        except ValueError as e:
            raise ValueError(f"❌ Failed to read Excel file: {e}")
        except Exception as e:
            raise RuntimeError(f"❌ Unexpected error while loading metadata: {e}")


    def extract_sample_code(self, s):
        return "".join(s.split("-")[1:]).strip().replace("\u00A0", "")

    def merge_data(self):
        self.merged = self.feature_table.merge(
            self.meta_seq,
            left_on="sample_code",
            right_on="ID échantillon",
            how="left"
        )

    def richness(self, row):
        return (row > 0).sum()

    def evenness(self, row):
        r = self.richness(row)
        sh = shannon(row.values, base=np.e)
        return sh / log(r) if r > 1 else 0

    def calculate_diversity_metrics(self):
        abundance_cols = self.feature_table.columns.difference(["sample_code"])

        self.merged[["shannon", "simpson", "richness", "evenness"]] = self.merged[abundance_cols].apply(
            lambda row: pd.Series({
                "shannon": shannon(row.values, base=np.e),
                "simpson": simpson(row.values),
                "richness": self.richness(row),
                "evenness": self.evenness(row)
            }), axis=1
        )

    def format_and_export(self):
        for col in ["shannon", "simpson", "richness", "evenness"]:
            self.merged[col] = self.merged[col].round(3)

        self.merged.fillna("N/A", inplace=True)

        self.final_df = self.merged[[
            "sample_code", "Patient", "Prélèvement", "Correpondance numérique",
            "shannon", "simpson", "richness", "evenness"
        ]]

        self.final_df.to_csv(self.output_path, index=False)
        print(f"✅ Final file exported : {self.output_path}")

    def run(self):
        self.load_feature_table()
        self.load_metadata()
        self.merge_data()
        self.calculate_diversity_metrics()
        self.format_and_export()

def main():
    parser = argparse.ArgumentParser(description="Calculate alpha diversity metrics from a feature table and metadata.")
    parser.add_argument("-f", "--feature_table", required=True, help="Path to the TSV feature table file.")
    parser.add_argument("-m", "--metadata", required=True, help="Path to the Excel metadata file.")
    parser.add_argument("-o", "--output", required=True, help="Output directory. Output file will be <feature_table_basename>_alpha_diversity_merged.csv")

    args = parser.parse_args()

    feature_table_path = Path(args.feature_table)
    if not feature_table_path.exists():
        print(f"[ERROR] The path '{feature_table_path}' does not exist. Please check the path and try again.", file=sys.stderr)
        exit(1)
        
    if feature_table_path.suffix.lower() != '.tsv':
        print("[ERROR] The feature table file must be a .tsv file.", file=sys.stderr)
        exit(1)

    base = feature_table_path.stem
    output_filename = f"{base}_alpha_diversity_merged.csv"
    if args.output:
        output_dir = Path(args.output)
        output_path = output_dir / output_filename
    else:
        output_path = Path.cwd() / output_filename

    try:
        calculator = DiversityMetricsCalculator(
            feature_table_path=str(feature_table_path),
            metadata_path=args.metadata,
            output_path=str(output_path)
        )
        calculator.run()
    except Exception as e:
        print(str(e))
        exit(1)

if __name__ == "__main__":
    main()