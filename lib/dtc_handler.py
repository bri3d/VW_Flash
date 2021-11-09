import csv
from udsoncan import Dtc
from . import constants


def dtcs_to_human(dtcs):
    csv_path = constants.internal_path("data", "dtcs.csv")
    output_dtcs = {}

    with open(csv_path, "r") as csv_file:
        reader = csv.DictReader(csv_file)
        for dtc in dtcs:
            dtc: Dtc = dtc
            dtc_id = dtc.id
            dtc_status = dtc.status
            for row in reader:
                if int(row["code"]) == dtc_id:
                    dtc_desc = (
                        f"{row['pcode']} : {row['name']}, {row['symbol']} Status: "
                    )
                    dtc_state = []
                    if dtc_status.test_failed:
                        dtc_state.append("Test Failed")
                    if dtc_status.test_failed_this_operation_cycle:
                        dtc_state.append("Test Failed This Operation Cycle")
                    if dtc_status.pending:
                        dtc_state.append("Pending")
                    if dtc_status.confirmed:
                        dtc_state.append("Confirmed")
                    if dtc_status.warning_indicator_requested:
                        dtc_state.append("Warning Light Active")
                    dtc_desc += ",".join(dtc_state)
                    output_dtcs[dtc_id] = dtc_desc

    return output_dtcs
