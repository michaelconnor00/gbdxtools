from gbdxtools import Interface
gbdx = Interface(run_local=True)

#########################################

# Locations for running local
local_input_data_root = '/Users/michaelconnor/hackathon'
local_input_raster = local_input_data_root + '/image'
iso_data = local_input_data_root + '/demo_output/iso'
final_data = local_input_data_root + '/demo_output/final'

# Locations for running on platform
remote_raster = 's3://gbd-customer-data/a157fdce-bb1d-42b3-96a9-66942896a787/denver_aop/'
iso_remote = 'hackathon/iso'
final_remote = 'hackathon/final'

#########################################

# Workflow Definition
iso = gbdx.Task("ENVI_ISODATAClassification")
iso.inputs.input_raster = local_input_raster

sieve = gbdx.Task("ENVI_ClassificationSieving")
sieve.inputs.input_raster = iso.outputs.output_raster_uri.value
sieve.inputs.minimum_size = 1
sieve.inputs.pixel_connectivity = 4

clump = gbdx.Task("ENVI_ClassificationClumping")
clump.inputs.input_raster = sieve.outputs.output_raster_uri.value

workflow = gbdx.Workflow([clump, sieve, iso])

workflow.savedata(
    iso.outputs.output_raster_uri,
    location=iso_data
)

workflow.savedata(
    clump.outputs.output_raster_uri,
    location=final_data
)

workflow.execute()
