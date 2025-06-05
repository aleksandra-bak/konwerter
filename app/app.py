from flask import Flask, request, render_template, send_file, abort
import os
import geopandas as gpd
import zipfile
import json
import time
import shutil
from datetime import datetime

app = Flask(__name__)

# LIMIT rozmiaru pliku: 20 MB
app.config["MAX_CONTENT_LENGTH"] = 20 * 1024 * 1024  # 20 MB

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def clean_old_files(folder, max_age_seconds=3600):
    now = time.time()
    for filename in os.listdir(folder):
        filepath = os.path.join(folder, filename)
        try:
            if os.path.isfile(filepath) and os.path.getmtime(filepath) < now - max_age_seconds:
                os.remove(filepath)
            elif os.path.isdir(filepath) and os.path.getmtime(filepath) < now - max_age_seconds:
                shutil.rmtree(filepath)
        except Exception as e:
            print(f"Błąd przy usuwaniu {filepath}: {e}")

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/process", methods=["POST"])
def process():
    # Czyść stare pliki
    clean_old_files(UPLOAD_FOLDER)
    clean_old_files(OUTPUT_FOLDER)

    # WALIDACJA pliku .gml
    gml_file = request.files["gml_file"]
    if not gml_file.filename.lower().endswith(".gml"):
        abort(400, description="Dozwolone są tylko pliki z rozszerzeniem .gml")

    # LOGOWANIE operacji
    client_ip = request.remote_addr
    zip_name = request.form["zip_name"].strip()
    log_entry = f"[{datetime.now()}] IP: {client_ip}, Plik: {gml_file.filename}, ZIP: {zip_name}.zip\n"
    with open("upload_log.txt", "a", encoding="utf-8") as log_file:
        log_file.write(log_entry)

    client_name = request.form["client_name"]
    farm_name = request.form["farm_name"]

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
            zipf.write(full_path, arcname=fname)

    if not os.path.exists(zip_path):
        abort(500, description="Nie udało się utworzyć pliku ZIP.")

    return send_file(zip_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
