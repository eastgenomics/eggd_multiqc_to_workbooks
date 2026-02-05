import pandas as pd
import openpyxl
import argparse
import json
import sys
from pathlib import Path

# get paths from bash commandline arguments
# improvement - use argparse
parser = argparse.ArgumentParser(
    description="Annotate sample workbooks with QC metrics extracted from MultiQC outputs.")
parser.add_argument("--multiqc_folder",
                     help="Name of the MultiQC folder under multiqc_inputs/")
parser.add_argument("--reports_folder",
                    help="Name of the reports folder under reports_inputs/")
parser.add_argument("--config_json",
                    help="JSON string mapping metric names to cell addresses")
parser.add_argument("--file_suffix",
                    help="string for customisable file suffix")
args = parser.parse_args()

multiqc_folder = args.multiqc_folder
reports_folder = args.reports_folder
config_json = args.config_json
file_suffix = args.file_suffix

# read config string into dict
config_file=json.loads(config_json)

print(config_file)

# set paths
multiqc_path = Path("multiqc_inputs") / multiqc_folder
reports_path = Path("reports_inputs") / reports_folder

print(multiqc_path)
print(reports_path)

def annotate_workbook(sample_row, reports_path):
    """
    Write QC values into specific location of excel file

    Args:
        sample_row (df): row of combined qc dataframe
    """
    # get needed column from qc table row

    sample = sample_row["Sample"]
    try:
        coverage = round(
            sample_row[
                "custom_content_custom_coverage-250x"
                ], 1
            )
        coverage_string = f"{coverage}%"

       # The freeMix score is % contamination predicted
       # conversion to percentage is now calculated during multiqc
        contamination = round(
            (sample_row[
                "verifybamid-FREEMIX"
                ]), 3
            )
        contamination_string = f"{contamination}%"

        # number of mapped_passed reads is now divided by 1M during multiqc
        total_reads_M = round(
            (sample_row[
                "samtools_flagstat-mapped_passed"
                ]), 1
            )

        fold80 = round(sample_row["FOLD_80_BASE_PENALTY"],1)

        insert_size = int(sample_row[
            "picard_insertsizemetrics-summed_median"
            ])
        insert_size_string = f"{insert_size} bp"

        try:
            # if doenst exist try sex check format
            sex_check = sample_row["matched"]
            sex_check_string = f"{sex_check}"
        except KeyError as err:
            print("Sex check value no found, looking for somalier")
            try:
                sex_check = sample_row["Match_Sexes"]
                sex_check_string = f"Somalier used. Sex match: {sex_check}"
            except KeyError as err:
                print(f"[WARN] Column {err} missing for sample {sample}; skipping row.")
                return
    except KeyError as err:
        print(f"[WARN] Column {err} missing for sample {sample}; skipping row.")
        return

    # get workbook corresponding to sample
    print(sample)
    path = reports_path / (sample + ".xlsx")
    try:
        sample_workbook = openpyxl.load_workbook(path)
    except FileNotFoundError:
        print("No workbook found for ", sample)
        return

    worksheet = sample_workbook['summary']

    # add "Somalier" to cell where header is currently added

    worksheet[config_file.get("cell_locations",{}).get("somalier_text")] = "Sex Check"

    # add data to sheet
    # want to pass cell locations in via a config for customisation
    worksheet[config_file.get("cell_locations",{}).get("250_coverage")] = coverage_string
    worksheet[config_file.get("cell_locations",{}).get("freemix")] = contamination_string
    worksheet[config_file.get("cell_locations",{}).get("M_reads")] = total_reads_M
    worksheet[config_file.get("cell_locations",{}).get("fold_80")] = fold80
    worksheet[config_file.get("cell_locations",{}).get("insert_size")] = insert_size_string
    worksheet[config_file.get("cell_locations",{}).get("somalier")] = sex_check_string

    # save file
    new_path= sample + file_suffix
    sample_workbook.save(new_path)

def create_combined_qc(multiqc_path):
    """
    Create one large table of all relevant QC metrics
    """
    # get general statistics, picard hs metrics and somalier

    general_stats_path = multiqc_path / config_file.get("multiqc_file_names",{}).get("general_stats_file")
    hsmetrics_path = multiqc_path / config_file.get("multiqc_file_names",{}).get("hsmetrics_file")
    sexcheck_path = multiqc_path / config_file.get("multiqc_file_names",{}).get("sexcheck_file")
    somalier_path = multiqc_path / config_file.get("multiqc_file_names",{}).get("somalier_file")

    # try finding sex check data, if not produced try somalier
    try:
        sexcheck  = pd.read_csv(sexcheck_path, sep="\t")
    except FileNotFoundError as e:
        print("sexcheck not found, looking for somalier")
        try:
            # if sex check file does not exist, find somalier check
            sexcheck  = pd.read_csv(somalier_path, sep="\t")
        except FileNotFoundError as e:
            sys.exit(f"[ERROR] Required MultiQC file missing: {e.filename}")
    except pd.errors.ParserError as e:
        sys.exit(f"[ERROR] Failed to parse MultiQC file: {e}")

    try:
        general_stats = pd.read_csv(general_stats_path, sep="\t")
        hsmetrics = pd.read_csv(hsmetrics_path, sep="\t")
    except FileNotFoundError as e:
        sys.exit(f"[ERROR] Required MultiQC file missing: {e.filename}")
    except pd.errors.ParserError as e:
        sys.exit(f"[ERROR] Failed to parse MultiQC file: {e}")

    # combine into one qc table
    hs_sexcheck = pd.merge(hsmetrics, sexcheck, on="Sample")
    combined_qc = pd.merge(general_stats, hs_sexcheck, on="Sample")

    return combined_qc

print("Beginning python")
qc_table = create_combined_qc(multiqc_path)
print(qc_table)
qc_table.apply(annotate_workbook, axis=1, reports_path = reports_path)

print("Reports annotated")


