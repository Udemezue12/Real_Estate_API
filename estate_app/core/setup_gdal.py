import os
import platform


def setup_gdal():
    system = platform.system()
    if system == "Windows":
        OSGEO4W = os.environ.get("OSGEO4W_ROOT", r"C:\OSGeo4W")
        gdal_dll = os.environ.get("GDAL_LIBRARY_PATH", r"C:\OSGeo4W\bin\gdal311.dll")

        if not os.path.exists(gdal_dll):
            print(" GDAL not found at expected path:", gdal_dll)
        else:
            os.environ["OSGEO4W_ROOT"] = OSGEO4W
            os.environ["GDAL_DATA"] = OSGEO4W + r"\share\gdal"
            os.environ["PROJ_LIB"] = OSGEO4W + r"\share\proj"
            os.environ["PATH"] = OSGEO4W + r"\bin;" + os.environ["PATH"]
            os.environ["GDAL_LIBRARY_PATH"] = gdal_dll
            print("GDAL configured for Windows at:", gdal_dll)
    else:
        print("GDAL available system-wide (Linux).")