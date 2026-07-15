import pyarrow.dataset as ds
import s3fs

fs = s3fs.S3FileSystem(anon=True)
dataset = ds.dataset("aodn-cloud-optimised/slocum_glider_delayed_qc.parquet",
                     filesystem=fs, format="parquet")

# Pull only EAC-region profiles, only the columns you need
import pyarrow.compute as pc
tbl = dataset.to_table(
    filter=(pc.field("LONGITUDE") > 150) & (pc.field("LONGITUDE") < 154)
            & (pc.field("LATITUDE") > -36) & (pc.field("LATITUDE") < -30),
    columns=["TIME", "LATITUDE", "LONGITUDE", "DEPTH", "TEMP", "PSAL"]
)
df = tbl.to_pandas()
