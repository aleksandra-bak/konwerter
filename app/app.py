
from flask import Flask, request, render_template, send_file, abort
import os
import geopandas as gpd
import zipfile
import json
import time

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/process", methods=["POST"])
def process():
    gml_file = request.files["gml_file"]
    client_name = request.form["client_name"]
    farm_name = request.form["farm_name"]
    zip_name = request.form["zip_name"].strip()

    gml_path = os.path.join(UPLOAD_FOLDER, gml_file.filename)
    shp_dir = os.path.join(OUTPUT_FOLDER, zip_name)
    zip_path = os.path.join(OUTPUT_FOLDER, f"{zip_name}.zip")

    os.makedirs(shp_dir, exist_ok=True)
    gml_file.save(gml_path)

    gdf = gpd.read_file(gml_path)
    gdf = gdf.to_crs(epsg=4326)

    new_gdf = gpd.GeoDataFrame()
    new_gdf["CLIENT_NAM"] = [client_name] * len(gdf)
    new_gdf["FARM_NAME"] = [farm_name] * len(gdf)
    new_gdf["FIELD_NAME"] = gdf["fid"]
    new_gdf["POLYGONTYP"] = [None] * len(gdf)
    new_gdf.set_geometry(gdf.geometry, inplace=True)
    new_gdf = new_gdf[["CLIENT_NAM", "FARM_NAME", "FIELD_NAME", "POLYGONTYP", "geometry"]]

    shp_path = os.path.join(shp_dir, f"{zip_name}.shp")
    new_gdf.to_file(shp_path)

    json_filename = f"{zip_name}-Deere-Metadata.json"
    json_path = os.path.join(shp_dir, json_filename)
    metadata = {
        "Version": "1.0",
        "ClientName": client_name,
        "FarmName": farm_name,
        "ShapeDataType": "Boundary"
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    time.sleep(1)
    if not os.path.isfile(shp_path):
        abort(500, description="Nie udało się utworzyć pliku SHP.")

    with zipfile.ZipFile(zip_path, "w") as zipf:
        for fname in os.listdir(shp_dir):
            full_path = os.path.join(shp_dir, fname)
            zipf.write(full_path, arcname=os.path.join(zip_name, fname))

    if not os.path.exists(zip_path):
        abort(500, description="Nie udało się utworzyć pliku ZIP.")

    return send_file(zip_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
