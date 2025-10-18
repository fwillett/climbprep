from pathlib import Path
import argparse
import json
import shutil
import subprocess

if __name__ == '__main__':
    argparser = argparse.ArgumentParser("Clean (denoise) a participant's functional data")
    argparser.add_argument('rootdir', help='will collate all files under rootdir with pattern **/*hemi-*_space-fsnative_desc-clean_bold.func.gii')
    argparser.add_argument('outfile', help='name of dtseries file to output, for example: /juice6/u/nlp/climblab/BIDS/moth/derivatives/clean/moth_fc_2mm/concat_fsnative.dtseries.nii')
    args = argparser.parse_args()

    root = Path(args.rootdir)
    pattern_l = "**/*hemi-L*_space-fsnative*_desc-clean_bold.func.gii"
    all_gii_l = sorted(root.glob(pattern_l))
    all_gii_r = []
    
    #for all left hemisphere files, find the matching right hemi partner
    for x in range(len(all_gii_l)):
        #get prefix of left hemisphere file
        l_filename = all_gii_l[x].name
        prefix = l_filename.split('hemi-L')[0]
    
        #find matching right hemisphere file
        pattern = "**/"+prefix+"hemi-R_space-fsnative_desc-clean_bold.func.gii"
        matching_right = sorted(root.glob(pattern))
        all_gii_r.append(matching_right[0])
    
    #get TR 
    import json, pathlib
    json_path = str(all_gii_l[0].parent) + '/' + all_gii_l[0].name.split('.func')[0] + '.json'
    TR = json.loads(pathlib.Path(json_path).read_text()).get("RepetitionTime")

    # Ensure Workbench is available
    wb = shutil.which("wb_command")
    if wb is None:
        raise EnvironmentError("Could not find 'wb_command' in PATH. Please add Connectome Workbench to your PATH and retry.")
    
    out_dt = Path(args.outfile).expanduser().absolute()
    out_dt.parent.mkdir(parents=True, exist_ok=True)
    
    # We'll create two temporary merged metric files (L and R), then build one dtseries
    td = Path(str(Path(args.outfile).parent) + '/dtseries_tmp').expanduser()
    td.mkdir(parents=True, exist_ok=True) 
    
    left_merged = td / "merged_L.func.gii"
    right_merged = td / "merged_R.func.gii"
    
    # 1) Merge all left metrics into one multi-frame .func.gii
    cmd_L = [wb, "-metric-merge", str(left_merged)]
    for L in all_gii_l:
        cmd_L += ["-metric", str(L)]
    print("Merging left metrics...")
    subprocess.run(cmd_L, check=True)
    
    # 2) Merge all right metrics into one multi-frame .func.gii
    cmd_R = [wb, "-metric-merge", str(right_merged)]
    for R in all_gii_r:
        cmd_R += ["-metric", str(R)]
    print("Merging right metrics...")
    subprocess.run(cmd_R, check=True)
    
    # 3) Create a dense timeseries CIFTI from the merged hemisphere metrics
    #    Note: we pass the TR, start at 0, units in seconds.
    cmd_C = [
        wb, "-cifti-create-dense-timeseries", str(out_dt),
        "-left-metric", str(left_merged),
        "-right-metric", str(right_merged),
        "-timestep", str(TR),
    ]
    print(f"Creating dtseries at:\n  {out_dt}")
    subprocess.run(cmd_C, check=True)

    print(f"Done! Wrote: {out_dt}")

    #delete temp
    shutil.rmtree(td)
