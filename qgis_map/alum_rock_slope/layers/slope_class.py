from pathlib import Path

from models import Layer, PaletteEntry, PalettedRenderer, ProcessingStep

slope_class = Layer(
    id="slope_class",
    name="Slope class (mechanical access)",
    type="raster",
    source="./data/USGS_slope_class.tif",
    provider="gdal",
    crs="EPSG:26910",
    visible=True,
    renderer=PalettedRenderer(
        opacity=0.7,
        entries=[
            PaletteEntry(value=1, color="#ffffd4", label="Flat (0-5°)"),
            PaletteEntry(value=2, color="#fed98e", label="Gentle (5-11°)"),
            PaletteEntry(value=3, color="#fe9929", label="Moderate (11-22°)"),
            PaletteEntry(value=4, color="#d95f0e", label="Steep (22-31°)"),
            PaletteEntry(value=5, color="#993404", label="Very steep (>31°)"),
        ],
    ),
    processing_step=ProcessingStep(
        description="Reclassify continuous slope degrees into five integer categories (1=flat, 2=gentle, 3=moderate, 4=steep, 5=very steep) based on mechanical treatment access breakpoints.",
        algorithm='gdal_calc.py -A {input} --A_band=1 -B {input} --B_band=2 --outfile={output} --calc="numpy.where(B>0, numpy.select([A<5, A<11, A<22, A<31], [1,2,3,4], 5), 0)" --type=Byte --NoDataValue=0 --quiet',
        depends_on=["slope_polygon"],
        output=Path("data/USGS_slope_class.tif"),
    ),
)
