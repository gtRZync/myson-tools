from pathlib import Path
import argparse
import sys

def generate_skip_list(path_dir: Path, output_dir:Path):
    if not path_dir.exists() or not path_dir.is_dir():
        print(f"[ERROR] The path {path_dir} is invalid. Please check the directory.", file=sys.stderr)
        sys.exit(1)
    if not output_dir.exists() or not output_dir.is_dir():
        print(f"[ERROR] The path {output_dir} is invalid. Please check the directory.", file=sys.stderr)
        sys.exit(1)
    subdir = '1_Raw_data/fastq_pass'
    path = path_dir / subdir

    subdirs = [p.name for p in path.iterdir() if p.is_dir() and 'patient' in p.name.lower()]
    file_name = f"{path_dir.name}_skip_list.txt"
    output_file = (output_dir / file_name)

    with open(output_file, 'w') as f:
        for name in subdirs:
            f.write(name + '\n')

    print(f"Written {len(subdirs)} entries to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate skip list file from folder names.")
    parser.add_argument("--path-dir", type=Path, required=True, help="Path to the directory")
    parser.add_argument("-o", "--output", type=Path, required=True, help="Output directory.Output file will be <run_basename>_skip_list.txt")
    

    args = parser.parse_args()
    generate_skip_list(args.path_dir, args.output)
