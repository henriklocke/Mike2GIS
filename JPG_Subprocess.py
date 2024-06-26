
import arcpy
import os
import datetime
##import pandas as pd

# Parameters - these need to be set accordingly
##project_path = r"J:\TOOLS\RAWN_Model_GIS_Tool\Tool_2_Create_Rawn\RAWN_Tool.aprx"  # Path to your ArcGIS Project file
##model_output_folder = r'J:\TOOLS\RAWN_Model_GIS_Tool\Tool_2_Create_Rawn\TestJPG'  # Path to your output folder
####node_id_df_path = r'C:\path\to\node_id.csv'  # Path to your node ID CSV file
##run_jpg = True

# Load the node ID dataframe
##node_id_df = pd.read_csv(node_id_df_path)

def main(project_path,jpg_folder):
    aprx = arcpy.mp.ArcGISProject(project_path)

    layouts = aprx.listLayouts()
    export_fails = []

    for layout in layouts:
        if layout.mapSeries is not None:
            map_series = layout.mapSeries
            map_series.refresh()

            page_numbers = range(1, map_series.pageCount + 1)
            reruns = 0

            for page_number in page_numbers:
                map_series.currentPageNumber = page_number
                output_filename = os.path.join(jpg_folder, f"{map_series.pageRow.Drains_To}.jpg")
                try:
                    layout.exportToJPEG(output_filename, resolution=300)
                except Exception as e:
                    print(f'WARNING! {map_series.pageRow.Drains_To} could not be made, try one more time')
                    try:
                        layout.exportToJPEG(output_filename, resolution=300)
                        print(f'OK, {map_series.pageRow.Drains_To} made in second try')
                    except Exception as e:
                        print(f'WARNING! {map_series.pageRow.Drains_To} could still not be made.')
                        export_fails.append(map_series.pageRow.Drains_To)
                print(f'Printing jpg {page_number} of {map_series.pageCount} at time {datetime.datetime.now()}')


    print(f'The following pages failed: {export_fails}')

if __name__ == "__main__":
    main(sys.argv[1],sys.argv[2])


