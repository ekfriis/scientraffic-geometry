
######################################
# Community identification workflow  #
######################################

# Put OSRM graph data into igraph format
%.igraph.pkl.gz: %.osrm
	./osrm2igraph.py $< $@

# Cluster nodes in graph using fast-greedy
%.communities.gz: %.igraph.pkl.gz find-communities.py 
	./find-communities.py --clusters 1000 $< $@

# Clean up clustering to remove artifacts
%.communities.cleaned.gz: %.communities.gz
	./clean-communities.py $< $@ --bbox -11820000 3384000 -11840000 3392000 --alphacut 10 --buffer 0.03 --convexity 0.5

# Make geo-json 
%.tesselation.json: %.communities.cleaned.gz tesselate-communities.py gis_data/ne_10m_urban_areas.shp gis_data/ne_10m_land.shp
	./tesselate-communities.py $< $@ --draw $*.pdf --AND gis_data/ne_10m_urban_areas.shp gis_data/ne_10m_land.shp

all: los-angeles.igraph.pkl.gz los-angeles.communities.gz \
  los-angeles.communities.cleaned.gz los-angeles.tesselation.json

######################################
# Downloading data 
######################################

# Land polygons
gis_data/ne_10m_land.zip: 
	mkdir -p gis_data
	cd gis_data && wget http://www.naturalearthdata.com/http//www.naturalearthdata.com/download/10m/physical/ne_10m_land.zip

gis_data/ne_10m_land.shp: gis_data/ne_10m_land.zip
	cd gis_data && unzip `basename $<`
	touch $@

# Urban areas
gis_data/ne_10m_urban_areas.zip:
	mkdir -p gis_data
	cd gis_data && wget http://www.naturalearthdata.com/http//www.naturalearthdata.com/download/10m/cultural/ne_10m_urban_areas.zip

gis_data/ne_10m_urban_areas.shp: gis_data/ne_10m_urban_areas.zip
	cd gis_data && unzip `basename $<`
	touch $@
